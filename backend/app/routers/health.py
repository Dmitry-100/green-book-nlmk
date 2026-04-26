from threading import Lock
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.cache import redis_cache_health_snapshot
from app.services.media import get_s3_client

router = APIRouter(tags=["health"])
_MINIO_HEALTH_CACHE_LOCK = Lock()
_MINIO_HEALTH_CACHE: dict | None = None
_MINIO_HEALTH_CACHE_EXPIRES_AT = 0.0


def _timed_dependency_result(check_name: str, fn) -> dict:
    started = perf_counter()
    try:
        fn()
        return {
            "status": "connected",
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "error": None,
            "dependency": check_name,
        }
    except Exception as exc:
        return {
            "status": "error",
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "error": str(exc)[:200],
            "dependency": check_name,
        }


def _check_redis() -> None:
    timeout_seconds = settings.health_dependency_timeout_ms / 1000
    redis_client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )
    redis_client.ping()


def _check_minio() -> None:
    get_s3_client().head_bucket(Bucket=settings.minio_bucket)


def reset_dependency_health_cache() -> None:
    global _MINIO_HEALTH_CACHE, _MINIO_HEALTH_CACHE_EXPIRES_AT
    with _MINIO_HEALTH_CACHE_LOCK:
        _MINIO_HEALTH_CACHE = None
        _MINIO_HEALTH_CACHE_EXPIRES_AT = 0.0


def _minio_dependency_result() -> dict:
    global _MINIO_HEALTH_CACHE, _MINIO_HEALTH_CACHE_EXPIRES_AT

    cache_ttl_seconds = settings.health_dependency_cache_ttl_seconds
    now = perf_counter()
    if cache_ttl_seconds > 0:
        with _MINIO_HEALTH_CACHE_LOCK:
            if (
                _MINIO_HEALTH_CACHE is not None
                and now < _MINIO_HEALTH_CACHE_EXPIRES_AT
            ):
                cached = dict(_MINIO_HEALTH_CACHE)
                cached["cached"] = True
                return cached

    result = _timed_dependency_result("minio", _check_minio)
    result["cached"] = False

    if cache_ttl_seconds > 0:
        with _MINIO_HEALTH_CACHE_LOCK:
            _MINIO_HEALTH_CACHE = dict(result)
            _MINIO_HEALTH_CACHE_EXPIRES_AT = perf_counter() + cache_ttl_seconds

    return result


def _dependency_snapshot(db: Session) -> dict:
    dependency_details = {
        "database": _timed_dependency_result("database", lambda: db.execute(text("SELECT 1"))),
        "redis": _timed_dependency_result("redis", _check_redis),
        "minio": _minio_dependency_result(),
    }
    dependency_status = {
        name: details["status"] for name, details in dependency_details.items()
    }
    return {
        "dependencies": dependency_status,
        "dependency_details": dependency_details,
        "cache": redis_cache_health_snapshot()["totals"],
    }


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db_check = _timed_dependency_result("database", lambda: db.execute(text("SELECT 1")))
    if db_check["status"] != "connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "database": "error", "details": db_check},
        )
    return {
        "status": "ok",
        "database": "connected",
        "details": db_check,
    }


@router.get("/api/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    snapshot = _dependency_snapshot(db)
    is_ready = all(value == "connected" for value in snapshot["dependencies"].values())
    response = {
        "status": "ready" if is_ready else "degraded",
        "dependencies": snapshot["dependencies"],
        "dependency_details": snapshot["dependency_details"],
        "cache": snapshot["cache"],
    }
    if not is_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response)
    return response


@router.get("/api/health/deps")
def dependencies_health(db: Session = Depends(get_db)):
    snapshot = _dependency_snapshot(db)
    degraded = any(
        value != "connected" for value in snapshot["dependencies"].values()
    )
    return {
        "status": "degraded" if degraded else "ok",
        "dependencies": snapshot["dependencies"],
        "dependency_details": snapshot["dependency_details"],
        "cache": snapshot["cache"],
    }


@router.get("/api/config/ymaps")
def ymaps_config(response: Response):
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.ymaps_config_cache_ttl_seconds}"
    )
    return {"apiKey": settings.ymaps_api_key}
