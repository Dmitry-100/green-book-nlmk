from app.services.metrics import (
    record_request_metric,
    request_metrics_prometheus_text,
    request_metrics_snapshot,
    reset_request_metrics,
)


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


def test_metrics_snapshot_includes_route_tail_latency_and_slow_routes():
    reset_request_metrics()

    for duration_ms in (10, 20, 30, 40, 500):
        record_request_metric(
            method="GET",
            route_path="/api/slow/{item_id}",
            fallback_path="/api/slow/123",
            status_code=200,
            duration_ms=duration_ms,
        )
    for duration_ms in (3, 4, 5):
        record_request_metric(
            method="GET",
            route_path="/api/fast",
            fallback_path="/api/fast",
            status_code=200,
            duration_ms=duration_ms,
        )

    snapshot = request_metrics_snapshot()

    assert snapshot["p95_duration_ms"] >= 250
    assert snapshot["p99_duration_ms"] >= snapshot["p95_duration_ms"]
    assert "slow_routes" in snapshot

    slow_route = next(
        item for item in snapshot["routes"] if item["route"] == "/api/slow/{item_id}"
    )
    assert slow_route["p95_duration_ms"] >= 250
    assert slow_route["p99_duration_ms"] >= slow_route["p95_duration_ms"]
    assert slow_route["max_duration_ms"] == 500
    assert snapshot["slow_routes"][0]["route"] == "/api/slow/{item_id}"


def test_metrics_prometheus_includes_duration_histograms():
    reset_request_metrics()
    record_request_metric(
        method="GET",
        route_path="/api/species/{species_id}",
        fallback_path="/api/species/170",
        status_code=200,
        duration_ms=42,
    )

    body = request_metrics_prometheus_text()

    assert "# TYPE greenbook_api_duration_ms histogram" in body
    assert 'greenbook_api_duration_ms_bucket{le="50"} 1' in body
    assert (
        'greenbook_api_route_duration_ms_bucket{route="/api/species/{species_id}",le="50"} 1'
        in body
    )
    assert (
        'greenbook_api_route_duration_ms_count{route="/api/species/{species_id}"} 1'
        in body
    )
