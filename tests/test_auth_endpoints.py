import pytest
from fastapi.testclient import TestClient

from app.config import config
from app.main import app
from app.rate_limiter import rate_limiter
from app.security.jwt import clear_denylist, verify_token
from app.storage import storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    original_key = config.secret_key
    config.secret_key = "test-secret-key"
    storage.reset_to_default()
    clear_denylist()
    rate_limiter._requests.clear()
    yield
    config.secret_key = original_key
    storage.reset_to_default()
    clear_denylist()
    rate_limiter._requests.clear()


def test_login_success():
    response = client.post(
        "/auth/login", json={"username": "demo", "password": "demo123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    access_payload = verify_token(data["access_token"])
    assert access_payload["sub"] == "demo-user"
    assert access_payload["role"] == "user"


def test_login_invalid_credentials():
    response = client.post(
        "/auth/login", json={"username": "demo", "password": "wrong"}
    )

    assert response.status_code == 401


def test_login_rate_limiting():
    for _ in range(5):
        client.post("/auth/login", json={"username": "demo", "password": "demo123"})

    response = client.post(
        "/auth/login", json={"username": "demo", "password": "demo123"}
    )
    assert response.status_code == 429


def test_refresh_token_success():
    login_response = client.post(
        "/auth/login", json={"username": "demo", "password": "demo123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/auth/token", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_invalid():
    response = client.post("/auth/token", json={"refresh_token": "invalid-token"})

    assert response.status_code == 401


def test_logout_success():
    login_response = client.post(
        "/auth/login", json={"username": "demo", "password": "demo123"}
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    retry_response = client.post("/auth/token", json={"refresh_token": refresh_token})
    assert retry_response.status_code == 401


def test_correlation_id_in_error_response():
    response = client.get("/highlights")

    assert response.status_code == 401
    data = response.json()
    assert "correlation_id" in data
    assert "type" in data
    assert data["type"] == "/errors/http-error"


def test_rate_limiting_create_highlight():
    login_response = client.post(
        "/auth/login", json={"username": "demo", "password": "demo123"}
    )
    token = login_response.json()["access_token"]

    for i in range(10):
        client.post(
            "/highlights",
            json={"text": f"Test {i}", "source": "Test", "tags": []},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.post(
        "/highlights",
        json={"text": "Should fail", "source": "Test", "tags": []},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 429
