def test_zone_by_point_rejects_out_of_range_coordinates(client):
    response = client.get("/api/map/zone-by-point?lat=95&lon=39.6")
    assert response.status_code == 422


def test_zone_by_point_accepts_valid_coordinates(client):
    response = client.get("/api/map/zone-by-point?lat=52.59&lon=39.6")
    assert response.status_code == 200
    assert "zones" in response.json()


def test_map_observations_rejects_invalid_bbox(client):
    response = client.get("/api/map/observations?bbox=invalid")
    assert response.status_code == 400


def test_map_observations_accepts_bbox(client):
    response = client.get("/api/map/observations?bbox=39.5,52.5,39.7,52.7")
    assert response.status_code == 200
    assert "features" in response.json()


def test_map_observations_rejects_unknown_group(client):
    response = client.get("/api/map/observations?group=unknown")
    assert response.status_code == 422


def test_map_observations_confirmed_returns_public_cache_header(client):
    response = client.get("/api/map/observations?bbox=39.5,52.5,39.7,52.7")
    assert response.status_code == 200
    assert "public" in response.headers.get("cache-control", "")


def test_map_observations_non_confirmed_returns_private_cache_header(
    client,
    ecologist_token,
):
    response = client.get(
        "/api/map/observations?status=on_review",
        headers={"Authorization": f"Bearer {ecologist_token}"},
    )
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "private, no-store"


def test_map_zones_returns_cache_header(client):
    response = client.get("/api/map/zones")
    assert response.status_code == 200
    assert "public" in response.headers.get("cache-control", "")
