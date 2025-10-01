from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_found_highlight():
    """Test error response for non-existent highlight"""
    r = client.get("/highlights/999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and body["error"]["code"] == "not_found"


def test_validation_error():
    """Test validation error response for invalid highlight data"""
    # Try to create highlight with empty text (should fail validation)
    invalid_data = {
        "text": "",  # Empty text should trigger validation error
        "source": "Valid Source",
        "tags": [],
    }
    r = client.post("/highlights", json=invalid_data)
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body


def test_update_not_found():
    """Test error when updating non-existent highlight"""
    update_data = {"text": "Updated text"}
    r = client.put("/highlights/999", json=update_data)
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and body["error"]["code"] == "not_found"


def test_delete_not_found():
    """Test error when deleting non-existent highlight"""
    r = client.delete("/highlights/999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and body["error"]["code"] == "not_found"
