from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_all_highlights():
    response = client.get("/highlights")
    assert response.status_code == 200
    data = response.json()
    assert "highlights" in data
    assert "total" in data
    assert data["total"] >= 2


def test_get_highlight_by_id():
    response = client.get("/highlights/1")
    assert response.status_code == 200
    data = response.json()
    assert "highlight" in data
    assert data["highlight"]["id"] == 1
    assert "Steve Jobs" in data["highlight"]["source"]


def test_get_nonexistent_highlight():
    response = client.get("/highlights/999")
    assert response.status_code == 404
    data = response.json()
    assert "type" in data
    assert "status" in data
    assert data["status"] == 404
    assert "correlation_id" in data


def test_create_highlight():
    new_highlight = {
        "text": "Test highlight text for API testing",
        "source": "Test Source Book",
        "tags": ["test", "api", "example"],
    }
    response = client.post("/highlights", json=new_highlight)
    assert response.status_code == 201
    data = response.json()
    assert "highlight" in data
    assert data["highlight"]["text"] == new_highlight["text"]
    assert data["highlight"]["source"] == new_highlight["source"]
    assert set(data["highlight"]["tags"]) == set(new_highlight["tags"])


def test_create_highlight_validation_error():
    invalid_highlight = {
        "text": "",
        "source": "Test Source",
        "tags": [],
    }
    response = client.post("/highlights", json=invalid_highlight)
    assert response.status_code == 422


def test_create_highlight_with_long_text():
    invalid_highlight = {
        "text": "x" * 2001,
        "source": "Test Source",
        "tags": [],
    }
    response = client.post("/highlights", json=invalid_highlight)
    assert response.status_code == 422


def test_create_highlight_too_many_tags():
    invalid_highlight = {
        "text": "Valid text",
        "source": "Test Source",
        "tags": [f"tag{i}" for i in range(11)],
    }
    response = client.post("/highlights", json=invalid_highlight)
    assert response.status_code == 422


def test_update_highlight():
    update_data = {
        "text": "Updated highlight text for testing",
        "tags": ["updated", "test", "api"],
    }
    response = client.put("/highlights/1", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["highlight"]["text"] == update_data["text"]
    assert set(data["highlight"]["tags"]) == set(update_data["tags"])


def test_update_partial_highlight():
    update_data = {"tags": ["philosophy", "wisdom", "partial-update"]}
    response = client.put("/highlights/2", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert "Einstein" in data["highlight"]["source"]
    assert set(data["highlight"]["tags"]) == set(update_data["tags"])


def test_update_nonexistent_highlight():
    update_data = {"text": "This should fail"}
    response = client.put("/highlights/999", json=update_data)
    assert response.status_code == 404


def test_delete_highlight():
    new_highlight = {
        "text": "Highlight to delete in test",
        "source": "Delete Test Source",
        "tags": ["delete", "test", "temporary"],
    }
    create_response = client.post("/highlights", json=new_highlight)
    created_id = create_response.json()["highlight"]["id"]

    response = client.delete(f"/highlights/{created_id}")
    assert response.status_code == 200
    data = response.json()
    assert "deleted_id" in data
    assert data["deleted_id"] == created_id

    get_response = client.get(f"/highlights/{created_id}")
    assert get_response.status_code == 404


def test_delete_nonexistent_highlight():
    response = client.delete("/highlights/999")
    assert response.status_code == 404


def test_filter_highlights_by_tag():
    response = client.get("/highlights?tag=motivation")
    assert response.status_code == 200
    data = response.json()
    assert len(data["highlights"]) >= 1
    for highlight in data["highlights"]:
        assert "motivation" in highlight["tags"]


def test_filter_highlights_by_multiple_word_tag():
    response = client.get("/highlights?tag=steve-jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data["highlights"]) >= 1


def test_filter_highlights_by_nonexistent_tag():
    response = client.get("/highlights?tag=nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["highlights"]) == 0


def test_export_markdown():
    response = client.get("/highlights/export/markdown")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "# Reading Highlights" in data["content"]
    assert "total_highlights" in data
    assert "Steve Jobs" in data["content"]
    assert "Einstein" in data["content"]


def test_export_markdown_with_tag_filter():
    response = client.get("/highlights/export/markdown?tag=philosophy")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["total_highlights"] >= 1
    assert "Einstein" in data["content"]


def test_export_markdown_with_nonexistent_tag():
    response = client.get("/highlights/export/markdown?tag=nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["total_highlights"] == 0
    assert "# Reading Highlights" in data["content"]


def test_highlights_sorting():
    response = client.get("/highlights")
    assert response.status_code == 200
    data = response.json()
    highlights = data["highlights"]

    assert len(highlights) >= 2

    for i in range(len(highlights) - 1):
        current_date = highlights[i]["created_at"]
        next_date = highlights[i + 1]["created_at"]
        assert current_date >= next_date


def test_create_highlight_tag_normalization():
    new_highlight = {
        "text": "Testing tag normalization",
        "source": "Test Source",
        "tags": ["  UPPERCASE  ", "Mixed-Case", "normal"],
    }
    response = client.post("/highlights", json=new_highlight)
    assert response.status_code == 201
    data = response.json()

    expected_tags = ["uppercase", "mixed-case", "normal"]
    assert set(data["highlight"]["tags"]) == set(expected_tags)
