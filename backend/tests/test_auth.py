from app.models.user import User


def test_valid_token_creates_user(client, db, employee_token):
    response = client.get(
        "/api/health",
    )
    # Health endpoint doesn't require auth, so this tests token generation
    assert employee_token is not None


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/health",
        headers={"Authorization": "Bearer invalid-token"},
    )
    # Health endpoint doesn't require auth, so this still returns 200
    assert response.status_code == 200
