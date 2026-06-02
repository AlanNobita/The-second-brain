

def test_health_endpoing(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200 
    assert "Second" in response.get_data(as_text=True)


def test_delete_session_endpoint(client):
    from app.models.db import save_message, get_message
    
    # Save a test message
    session_id = "test-session-xyz"
    save_message(session_id, "user", "Test message content")
    
    # Assert it was saved
    messages = get_message(session_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "Test message content"
    
    # Call the DELETE endpoint
    response = client.delete(f"/session/{session_id}")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    
    # Verify the message is deleted
    remaining = get_message(session_id)
    assert len(remaining) == 0


    