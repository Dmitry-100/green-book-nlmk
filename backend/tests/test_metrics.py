from app.services.metrics import reset_request_metrics


def test_metrics_endpoint_requires_admin(client, employee_token, admin_token):
    reset_request_metrics()

    forbidden = client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert forbidden.status_code == 403

    allowed = client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allowed.status_code == 200
    payload = allowed.json()
    assert "requests_total" in payload
    assert "routes" in payload

    forbidden_prometheus = client.get(
        "/api/metrics/prometheus",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert forbidden_prometheus.status_code == 403

    allowed_prometheus = client.get(
        "/api/metrics/prometheus",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allowed_prometheus.status_code == 200
    assert "greenbook_api_requests_total" in allowed_prometheus.text


def test_metrics_endpoint_collects_request_stats(client, admin_token):
    reset_request_metrics()

    health_response = client.get("/api/health")
    assert health_response.status_code == 200

    species_response = client.get("/api/species")
    assert species_response.status_code == 200

    metrics_response = client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert metrics_response.status_code == 200
    payload = metrics_response.json()

    assert payload["requests_total"] >= 2
    assert payload["status_counts"].get("200", 0) >= 2
    assert payload["method_counts"].get("GET", 0) >= 2

    route_labels = {item["route"] for item in payload["routes"]}
    assert "/api/health" in route_labels
    assert "/api/species" in route_labels


def test_metrics_prometheus_includes_cache_and_route_metrics(client, admin_token):
    reset_request_metrics()

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/species").status_code == 200

    response = client.get(
        "/api/metrics/prometheus",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.text

    assert "greenbook_api_uptime_seconds" in body
    assert 'greenbook_api_route_requests_total{route="/api/health"}' in body
    assert "greenbook_cache_stores_total" in body
    assert "greenbook_cache_store_up{" in body
