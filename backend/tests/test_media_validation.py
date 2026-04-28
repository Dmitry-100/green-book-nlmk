from tests.conftest import make_token
import app.routers.observations as observations_router


def test_upload_url_rejects_unsupported_content_type(client):
    token = make_token(
        external_id="media-test-001",
        name="Media Test",
        email="media-test-001@nlmk.com",
        role="employee",
    )

    response = client.post(
        "/api/observations/upload-url",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "filename": "payload.txt",
            "content_type": "text/plain",
            "file_size": 128,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported media content_type"


def test_upload_url_rejects_large_files(client):
    token = make_token(
        external_id="media-test-002",
        name="Media Test",
        email="media-test-002@nlmk.com",
        role="employee",
    )

    response = client.post(
        "/api/observations/upload-url",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "filename": "bird.jpg",
            "content_type": "image/jpeg",
            "file_size": 11 * 1024 * 1024,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File is too large"


def test_backend_upload_accepts_file_without_exposing_storage_url(client, monkeypatch):
    token = make_token(
        external_id="media-test-003",
        name="Media Test",
        email="media-test-003@nlmk.com",
        role="employee",
    )

    monkeypatch.setattr(
        observations_router,
        "store_uploaded_file",
        lambda filename, content_type, payload: {
            "s3_key": f"observations/{filename}",
            "content_type": content_type,
            "file_size": len(payload),
        },
        raising=False,
    )

    response = client.post(
        "/api/observations/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bird.jpg", b"fake-jpeg-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "s3_key": "observations/bird.jpg",
        "content_type": "image/jpeg",
        "file_size": 15,
    }
