import pytest
from fastapi.testclient import TestClient

from app.config import config
from app.main import app
from app.security.jwt import clear_denylist, issue_access_token
from app.storage import storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    original_key = config.secret_key
    config.secret_key = "test-secret-key"
    storage.reset_to_default()
    clear_denylist()
    yield
    config.secret_key = original_key
    storage.reset_to_default()
    clear_denylist()


@pytest.fixture
def auth_headers():
    token = issue_access_token(sub="demo-user", role="user")
    return {"Authorization": f"Bearer {token}"}


def test_rfc7807_contract_not_found(auth_headers):
    r = client.get("/highlights/999", headers=auth_headers)
    assert r.status_code == 404
    body = r.json()

    assert "type" in body
    assert "title" in body
    assert "status" in body
    assert "detail" in body
    assert "correlation_id" in body

    assert body["status"] == 404
    assert body["type"] == "/errors/not-found"
    assert "not found" in body["detail"].lower()

    assert len(body["correlation_id"]) == 36
    assert body["correlation_id"].count("-") == 4


def test_rfc7807_validation_error(auth_headers):
    invalid_data = {
        "text": "",
        "source": "Valid Source",
        "tags": [],
    }
    r = client.post("/highlights", json=invalid_data, headers=auth_headers)
    assert r.status_code == 422
    body = r.json()

    assert body["type"] == "/errors/validation"
    assert body["title"] == "Validation Error"
    assert body["status"] == 422
    assert "correlation_id" in body
    assert "validation_errors" in body


def test_rfc7807_update_not_found(auth_headers):
    update_data = {"text": "Updated text"}
    r = client.put("/highlights/999", json=update_data, headers=auth_headers)
    assert r.status_code == 404
    body = r.json()

    assert body["type"] == "/errors/not-found"
    assert body["status"] == 404
    assert "correlation_id" in body


def test_rfc7807_delete_not_found(auth_headers):
    r = client.delete("/highlights/999", headers=auth_headers)
    assert r.status_code == 404
    body = r.json()

    assert body["type"] == "/errors/not-found"
    assert body["status"] == 404
    assert "correlation_id" in body


def test_rfc7807_too_many_tags(auth_headers):
    invalid_data = {
        "text": "Valid text",
        "source": "Valid source",
        "tags": [f"tag{i}" for i in range(15)],
    }
    r = client.post("/highlights", json=invalid_data, headers=auth_headers)
    assert r.status_code == 422
    body = r.json()

    assert body["type"] == "/errors/validation"
    assert body["status"] == 422
    assert "correlation_id" in body
