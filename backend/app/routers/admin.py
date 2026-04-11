import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_role
from app.config import settings
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.observation import (
    IncidentStatus,
    Observation,
    ObservationStatus,
    ObsMedia,
    MediaProcessingStatus,
)
from app.models.site_zone import SiteZone
from app.models.species import Species
from app.models.user import User, UserRole
from app.schemas.audit import (
    AuditEventListResponse,
    AuditEventResponse,
    AuditPurgeResponse,
)
from app.services.audit import audit_event
from app.services.cache import redis_cache_health_snapshot
from app.services.media_pipeline import run_media_processing_batch
from app.services.metrics import request_metrics_snapshot

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _build_ops_summary_payload(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    species_total = db.query(Species.id).count()
    observations_total = db.query(Observation.id).count()
    on_review = (
        db.query(Observation.id)
        .filter(Observation.status == ObservationStatus.on_review)
        .count()
    )
    needs_data = (
        db.query(Observation.id)
        .filter(Observation.status == ObservationStatus.needs_data)
        .count()
    )
    confirmed = (
        db.query(Observation.id)
        .filter(Observation.status == ObservationStatus.confirmed)
        .count()
    )
    rejected = (
        db.query(Observation.id)
        .filter(Observation.status == ObservationStatus.rejected)
        .count()
    )
    open_incidents = (
        db.query(Observation.id)
        .filter(
            Observation.is_incident.is_(True),
            Observation.incident_status.in_(
                [IncidentStatus.new, IncidentStatus.in_progress]
            ),
        )
        .count()
    )
    unread_notifications = (
        db.query(Notification.id)
        .filter(Notification.is_read.is_(False))
        .count()
    )
    audit_total = db.query(AuditLog.id).count()
    audit_last_24h = (
        db.query(AuditLog.id)
        .filter(AuditLog.created_at >= day_ago)
        .count()
    )
    media_pending = (
        db.query(ObsMedia.id)
        .filter(ObsMedia.processing_status == MediaProcessingStatus.pending)
        .count()
    )
    media_processing = (
        db.query(ObsMedia.id)
        .filter(ObsMedia.processing_status == MediaProcessingStatus.processing)
        .count()
    )
    media_ready = (
        db.query(ObsMedia.id)
        .filter(ObsMedia.processing_status == MediaProcessingStatus.ready)
        .count()
    )
    media_failed = (
        db.query(ObsMedia.id)
        .filter(ObsMedia.processing_status == MediaProcessingStatus.failed)
        .count()
    )
    pending_oldest_created_at = (
        db.query(func.min(ObsMedia.created_at))
        .filter(ObsMedia.processing_status == MediaProcessingStatus.pending)
        .scalar()
    )
    pending_oldest_age_seconds = 0
    if pending_oldest_created_at is not None:
        oldest = pending_oldest_created_at
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        pending_oldest_age_seconds = max(int((now - oldest).total_seconds()), 0)

    cache_snapshot = redis_cache_health_snapshot()

    return {
        "generated_at": now.isoformat(),
        "catalog": {
            "species_total": species_total,
        },
        "pipeline": {
            "observations_total": observations_total,
            "on_review": on_review,
            "needs_data": needs_data,
            "confirmed": confirmed,
            "rejected": rejected,
        },
        "incidents": {
            "open_incidents": open_incidents,
        },
        "notifications": {
            "unread_total": unread_notifications,
        },
        "audit": {
            "events_total": audit_total,
            "events_last_24h": audit_last_24h,
        },
        "media_pipeline": {
            "pending": media_pending,
            "processing": media_processing,
            "ready": media_ready,
            "failed": media_failed,
            "pending_oldest_age_seconds": pending_oldest_age_seconds,
        },
        "cache": cache_snapshot,
        "metrics": request_metrics_snapshot(),
    }


@router.post("/zones/import")
async def import_zones(
    file: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Import site zones from a GeoJSON file."""
    filename = file.filename or ""
    if not filename.endswith(".geojson") and not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only GeoJSON files are supported")

    content = await file.read()
    try:
        geojson = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    features = geojson.get("features", [])
    if not features:
        raise HTTPException(status_code=400, detail="No features found in GeoJSON")

    imported = 0
    for feature in features:
        geom = feature.get("geometry")
        props = feature.get("properties", {})
        if not geom:
            continue
        # Convert to WKT via Shapely
        shapely_geom = shape(geom)
        wkt = WKTElement(shapely_geom.wkt, srid=4326)
        zone = SiteZone(
            name=props.get("name", f"Zone {imported + 1}"),
            group=props.get("group"),
            geom=wkt,
            source=filename,
        )
        db.add(zone)
        imported += 1

    db.commit()
    audit_event(
        action="admin.zones_import",
        actor=user,
        target_type="site_zone",
        details={"imported": imported, "filename": filename},
        db=db,
    )
    return {"imported": imported, "filename": filename}


@router.get("/audit/events", response_model=AuditEventListResponse)
def list_audit_events(
    action: str | None = Query(default=None, min_length=1, max_length=100),
    target_type: str | None = Query(default=None, min_length=1, max_length=100),
    actor_user_id: int | None = Query(default=None, gt=0),
    outcome: str | None = Query(default=None, min_length=1, max_length=50),
    request_id: str | None = Query(default=None, min_length=1, max_length=64),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    include_total: bool = Query(default=True),
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if outcome:
        query = query.filter(AuditLog.outcome == outcome)
    if request_id:
        query = query.filter(AuditLog.request_id == request_id)
    if created_from:
        query = query.filter(AuditLog.created_at >= created_from)
    if created_to:
        query = query.filter(AuditLog.created_at <= created_to)

    total = query.count() if include_total else None
    items = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("/audit/purge", response_model=AuditPurgeResponse)
def purge_audit_events(
    older_than_days: int = Query(
        default=settings.audit_log_retention_days,
        ge=1,
        le=36500,
    ),
    dry_run: bool = Query(default=True),
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    delete_query = db.query(AuditLog).filter(AuditLog.created_at < cutoff)
    candidates = delete_query.count()
    deleted = 0

    if not dry_run:
        if candidates > 0:
            deleted = delete_query.delete(synchronize_session=False)
            db.commit()
        audit_event(
            action="admin.audit_purge",
            actor=user,
            target_type="audit_log",
            outcome="success",
            details={
                "older_than_days": older_than_days,
                "cutoff_iso": cutoff.isoformat(),
                "candidates": candidates,
                "deleted": deleted,
            },
            db=db,
        )

    return AuditPurgeResponse(
        dry_run=dry_run,
        older_than_days=older_than_days,
        cutoff_iso=cutoff.isoformat(),
        candidates=candidates,
        deleted=deleted,
    )


@router.get("/ops/summary")
def ops_summary(
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    del user
    return _build_ops_summary_payload(db)


@router.post("/ops/media/process")
def process_pending_media(
    batch_size: int = Query(
        default=settings.media_processing_batch_size,
        ge=1,
        le=500,
    ),
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    del user
    return run_media_processing_batch(db, batch_size=batch_size)


@router.get("/ops/alerts")
def ops_alerts(
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    del user
    summary = _build_ops_summary_payload(db)
    alerts: list[dict] = []

    on_review = summary["pipeline"]["on_review"]
    if on_review > settings.ops_alert_on_review_threshold:
        alerts.append({
            "code": "validation_queue_high",
            "severity": "warning",
            "message": (
                "Validation queue is above threshold: "
                f"{on_review} > {settings.ops_alert_on_review_threshold}"
            ),
            "value": on_review,
            "threshold": settings.ops_alert_on_review_threshold,
        })

    open_incidents = summary["incidents"]["open_incidents"]
    if open_incidents > settings.ops_alert_open_incidents_threshold:
        alerts.append({
            "code": "open_incidents_high",
            "severity": "critical",
            "message": (
                "Open incidents are above threshold: "
                f"{open_incidents} > {settings.ops_alert_open_incidents_threshold}"
            ),
            "value": open_incidents,
            "threshold": settings.ops_alert_open_incidents_threshold,
        })

    error_rate = float(summary["metrics"]["error_rate_percent"])
    if error_rate > settings.ops_alert_error_rate_percent_threshold:
        alerts.append({
            "code": "api_error_rate_high",
            "severity": "critical",
            "message": (
                "API error rate is above threshold: "
                f"{error_rate} > {settings.ops_alert_error_rate_percent_threshold}"
            ),
            "value": error_rate,
            "threshold": settings.ops_alert_error_rate_percent_threshold,
        })

    media_pending = int(summary["media_pipeline"]["pending"])
    if media_pending > settings.ops_alert_media_pending_threshold:
        alerts.append({
            "code": "media_queue_depth_high",
            "severity": "warning",
            "message": (
                "Media processing queue depth is above threshold: "
                f"{media_pending} > {settings.ops_alert_media_pending_threshold}"
            ),
            "value": media_pending,
            "threshold": settings.ops_alert_media_pending_threshold,
        })

    media_pending_age = int(summary["media_pipeline"]["pending_oldest_age_seconds"])
    if media_pending_age > settings.ops_alert_media_pending_age_seconds_threshold:
        alerts.append({
            "code": "media_queue_lag_high",
            "severity": "warning",
            "message": (
                "Oldest pending media item age is above threshold: "
                f"{media_pending_age}s > "
                f"{settings.ops_alert_media_pending_age_seconds_threshold}s"
            ),
            "value": media_pending_age,
            "threshold": settings.ops_alert_media_pending_age_seconds_threshold,
        })

    media_failed = int(summary["media_pipeline"]["failed"])
    if media_failed > settings.ops_alert_media_failed_threshold:
        alerts.append({
            "code": "media_processing_failed_high",
            "severity": "critical",
            "message": (
                "Failed media items are above threshold: "
                f"{media_failed} > {settings.ops_alert_media_failed_threshold}"
            ),
            "value": media_failed,
            "threshold": settings.ops_alert_media_failed_threshold,
        })

    degraded_caches = int(summary["cache"]["totals"]["degraded_stores"])
    if degraded_caches > settings.ops_alert_cache_degraded_stores_threshold:
        alerts.append({
            "code": "cache_backend_degraded",
            "severity": "critical",
            "message": (
                "Degraded redis-backed caches are above threshold: "
                f"{degraded_caches} > {settings.ops_alert_cache_degraded_stores_threshold}"
            ),
            "value": degraded_caches,
            "threshold": settings.ops_alert_cache_degraded_stores_threshold,
        })

    return {
        "generated_at": summary["generated_at"],
        "status": "alert" if alerts else "ok",
        "alerts": alerts,
        "thresholds": {
            "on_review": settings.ops_alert_on_review_threshold,
            "open_incidents": settings.ops_alert_open_incidents_threshold,
            "error_rate_percent": settings.ops_alert_error_rate_percent_threshold,
            "media_pending": settings.ops_alert_media_pending_threshold,
            "media_pending_age_seconds": (
                settings.ops_alert_media_pending_age_seconds_threshold
            ),
            "media_failed": settings.ops_alert_media_failed_threshold,
            "cache_degraded_stores": (
                settings.ops_alert_cache_degraded_stores_threshold
            ),
        },
        "snapshot": {
            "on_review": on_review,
            "open_incidents": open_incidents,
            "error_rate_percent": error_rate,
            "media_pending": media_pending,
            "media_pending_age_seconds": media_pending_age,
            "media_failed": media_failed,
            "cache_degraded_stores": degraded_caches,
        },
    }
