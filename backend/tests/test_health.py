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
