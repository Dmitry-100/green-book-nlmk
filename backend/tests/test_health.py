from app.routers import health as health_router


def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_readiness_endpoint_is_available(client):
    response = client.get("/api/health/ready")
    assert response.status_code in {200, 503}
    data = response.json()

    if response.status_code == 200:
        assert data["status"] == "ready"
        assert data["dependencies"]["database"] == "connected"
        assert "dependency_details" in data
        assert "cache" in data
    else:
        assert data["detail"]["status"] == "degraded"
        assert "dependencies" in data["detail"]
        assert "dependency_details" in data["detail"]


def test_health_response_has_request_id(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_ymaps_config_cache_header(client):
    response = client.get("/api/config/ymaps")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "")
    assert "public" in cache_control
    assert "max-age=3600" in cache_control


def test_dependencies_health_endpoint(client):
    response = client.get("/api/health/deps")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "dependencies" in payload
    assert "dependency_details" in payload
    assert "cache" in payload


def test_minio_health_check_uses_bucket_head(monkeypatch):
    calls: list[tuple[str, str]] = []

    class FakeS3Client:
        def head_bucket(self, *, Bucket: str) -> None:
            calls.append(("head_bucket", Bucket))

        def list_buckets(self) -> None:
            raise AssertionError("health check must not list all buckets")

    monkeypatch.setattr(health_router, "get_s3_client", lambda: FakeS3Client())

    health_router._check_minio()

    assert calls == [("head_bucket", health_router.settings.minio_bucket)]


def test_minio_dependency_result_reuses_short_cache(monkeypatch):
    calls = 0

    class FakeS3Client:
        def head_bucket(self, *, Bucket: str) -> None:
            nonlocal calls
            calls += 1

    monkeypatch.setattr(health_router, "get_s3_client", lambda: FakeS3Client())
    monkeypatch.setattr(health_router.settings, "health_dependency_cache_ttl_seconds", 30)
    health_router.reset_dependency_health_cache()

    first = health_router._minio_dependency_result()
    second = health_router._minio_dependency_result()

    assert first["status"] == "connected"
    assert first["cached"] is False
    assert second["status"] == "connected"
    assert second["cached"] is True
    assert calls == 1
