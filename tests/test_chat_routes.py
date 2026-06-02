"""Tests for the /chat/send endpoint, including source attribution."""
from unittest.mock import patch


def _mock_ai_response(reply="Hello!", suggestion=None, sources=None):
    """Build a side_effect that returns a (reply, suggestion, sources) tuple."""
    return lambda *args, **kwargs: (reply, suggestion, sources or [])


def test_chat_send_returns_reply(client):
    with patch("app.routes.chat.get_ai_response",
                side_effect=_mock_ai_response(reply="Hi there")):
        response = client.post("/chat/send",
                               json={"message": "Hello"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["reply"] == "Hi there"
        assert "session_id" in data


def test_chat_send_includes_sources(client):
    sources = [
        {"type": "youtube", "title": "Test Video", "url": "https://youtube.com/watch?v=abc", "session_id": "yt_abc"},
    ]
    with patch("app.routes.chat.get_ai_response",
                side_effect=_mock_ai_response(reply="Based on the video", sources=sources)):
        response = client.post("/chat/send",
                               json={"message": "Tell me about that video"})
        assert response.status_code == 200
        data = response.get_json()
        assert "sources" in data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["type"] == "youtube"
        assert data["sources"][0]["title"] == "Test Video"


def test_chat_send_omits_sources_when_empty(client):
    with patch("app.routes.chat.get_ai_response",
                side_effect=_mock_ai_response(reply="No sources here", sources=[])):
        response = client.post("/chat/send",
                               json={"message": "What is X?"})
        assert response.status_code == 200
        data = response.get_json()
        assert "sources" not in data


def test_chat_send_includes_suggestion(client):
    suggestion = {"text": "Related to past chat", "session_id": "abc", "preview": "..."}
    with patch("app.routes.chat.get_ai_response",
                side_effect=_mock_ai_response(reply="Yes", suggestion=suggestion)):
        response = client.post("/chat/send",
                               json={"message": "Tell me more"})
        assert response.status_code == 200
        data = response.get_json()
        assert "suggestion" in data
        assert data["suggestion"]["text"] == "Related to past chat"


def test_chat_send_preserves_session_id(client):
    with patch("app.routes.chat.get_ai_response",
                side_effect=_mock_ai_response(reply="Echo")):
        response = client.post("/chat/send",
                               json={"message": "Test", "session_id": "my-session-123"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["session_id"] == "my-session-123"
