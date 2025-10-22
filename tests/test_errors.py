from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_rfc7807_contract_not_found():
    """Test RFC 7807 error format for non-existent highlight"""
    r = client.get("/highlights/999")
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


def test_rfc7807_validation_error():
    """Test RFC 7807 format for validation errors"""
    invalid_data = {
        "text": "",
        "source": "Valid Source",
        "tags": [],
    }
    r = client.post("/highlights", json=invalid_data)
    assert r.status_code == 422
    body = r.json()

    assert body["type"] == "/errors/validation"
    assert body["title"] == "Validation Error"
    assert body["status"] == 422
    assert "correlation_id" in body
    assert "validation_errors" in body


def test_rfc7807_update_not_found():
    """Test RFC 7807 error when updating non-existent highlight"""
    update_data = {"text": "Updated text"}
    r = client.put("/highlights/999", json=update_data)
    assert r.status_code == 404
    body = r.json()

    assert body["type"] == "/errors/not-found"
    assert body["status"] == 404
    assert "correlation_id" in body


def test_rfc7807_delete_not_found():
    """Test RFC 7807 error when deleting non-existent highlight"""
    r = client.delete("/highlights/999")
    assert r.status_code == 404
    body = r.json()

    assert body["type"] == "/errors/not-found"
    assert body["status"] == 404
    assert "correlation_id" in body


def test_rfc7807_too_many_tags():
    """Test validation error for too many tags"""
    invalid_data = {
        "text": "Valid text",
        "source": "Valid source",
        "tags": [f"tag{i}" for i in range(15)],
    }
    r = client.post("/highlights", json=invalid_data)
    assert r.status_code == 422
    body = r.json()

    assert body["type"] == "/errors/validation"
    assert body["status"] == 422
    assert "correlation_id" in body
