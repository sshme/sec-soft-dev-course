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


def test_missing_authorization_header():
    response = client.get("/highlights")
    assert response.status_code == 401
    assert "correlation_id" in response.json()


def test_invalid_authorization_format():
    response = client.get(
        "/highlights", headers={"Authorization": "InvalidFormat token123"}
    )
    assert response.status_code == 401


def test_user_can_access_own_highlights():
    token = issue_access_token(sub="demo-user", role="user")
    response = client.get("/highlights", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["highlights"]) == 2


def test_user_cannot_access_other_user_highlights():
    token = issue_access_token(sub="other-user", role="user")
    response = client.get("/highlights", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["highlights"]) == 0


def test_get_highlight_returns_404_for_other_owner():
    token = issue_access_token(sub="other-user", role="user")
    response = client.get("/highlights/1", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404


def test_admin_can_access_any_highlight():
    storage.create(
        text="Admin test", source="Test", tags=["admin"], owner_id="another-user"
    )

    token = issue_access_token(sub="admin-user", role="admin")
    response = client.get("/highlights/3", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_create_highlight_with_owner():
    token = issue_access_token(sub="new-user", role="user")
    response = client.post(
        "/highlights",
        json={"text": "New highlight", "source": "Test Source", "tags": ["test"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["highlight"]["owner_id"] == "new-user"


def test_update_own_highlight():
    token = issue_access_token(sub="demo-user", role="user")
    response = client.put(
        "/highlights/1",
        json={"text": "Updated text"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["highlight"]["text"] == "Updated text"


def test_update_other_user_highlight_returns_404():
    token = issue_access_token(sub="other-user", role="user")
    response = client.put(
        "/highlights/1",
        json={"text": "Trying to update"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_delete_own_highlight():
    token = issue_access_token(sub="demo-user", role="user")
    response = client.delete(
        "/highlights/1", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_delete_other_user_highlight_returns_404():
    token = issue_access_token(sub="other-user", role="user")
    response = client.delete(
        "/highlights/1", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
