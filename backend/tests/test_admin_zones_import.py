import json

from app.models.audit_log import AuditLog
from app.models.site_zone import SiteZone
from app.models.user import User


def test_zones_import_requires_admin(client, employee_token):
    response = client.post(
        "/api/admin/zones/import",
        headers={"Authorization": f"Bearer {employee_token}"},
        files={
            "file": (
                "zones.geojson",
                json.dumps({"type": "FeatureCollection", "features": []}),
                "application/geo+json",
            )
        },
    )
    assert response.status_code == 403


def test_zones_import_rejects_invalid_extension(client, admin_token):
    response = client.post(
        "/api/admin/zones/import",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "zones.txt",
                "not-geojson",
                "text/plain",
            )
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only GeoJSON files are supported"


def test_zones_import_rejects_invalid_json(client, admin_token):
    response = client.post(
        "/api/admin/zones/import",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "zones.geojson",
                "{invalid-json",
                "application/geo+json",
            )
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON"


def test_zones_import_rejects_empty_features(client, admin_token):
    response = client.post(
        "/api/admin/zones/import",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "zones.geojson",
                json.dumps({"type": "FeatureCollection", "features": []}),
                "application/geo+json",
            )
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No features found in GeoJSON"


def test_zones_import_persists_zones_and_audit_event(client, db, admin_token):
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Zone A", "group": "north"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [39.60, 52.58],
                            [39.61, 52.58],
                            [39.61, 52.59],
                            [39.60, 52.59],
                            [39.60, 52.58],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"group": "south"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [39.62, 52.58],
                            [39.63, 52.58],
                            [39.63, 52.59],
                            [39.62, 52.59],
                            [39.62, 52.58],
                        ]
                    ],
                },
            },
        ],
    }

    response = client.post(
        "/api/admin/zones/import",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "zones.geojson",
                json.dumps(payload),
                "application/geo+json",
            )
        },
    )
    assert response.status_code == 200
    assert response.json() == {"imported": 2, "filename": "zones.geojson"}

    zones = db.query(SiteZone).order_by(SiteZone.id.asc()).all()
    assert len(zones) == 2
    assert zones[0].name == "Zone A"
    assert zones[0].group == "north"
    assert zones[0].source == "zones.geojson"
    assert zones[1].name == "Zone 2"
    assert zones[1].group == "south"
    assert zones[1].source == "zones.geojson"

    admin_user = (
        db.query(User).filter(User.external_id == "admin-001").first()
    )
    assert admin_user is not None
    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "admin.zones_import")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_log is not None
    assert audit_log.actor_user_id == admin_user.id
    assert audit_log.target_type == "site_zone"
    assert audit_log.details["imported"] == 2
    assert audit_log.details["filename"] == "zones.geojson"
