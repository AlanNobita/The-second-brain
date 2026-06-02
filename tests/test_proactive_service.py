from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


_old_date = (datetime.now() - timedelta(days=2)).isoformat()


@patch("app.services.proactive_service.semantic_search")
@patch("app.services.proactive_service.get_messages_by_ids")
def test_get_proactive_suggestions_no_results(mock_get_msgs, mock_search):
    mock_search.return_value = {"ids": [[]], "distances": [[]]}
    from app.services.proactive_service import get_proactive_suggestions
    result = get_proactive_suggestions("hello world", "session_1")
    assert result == []


@patch("app.services.proactive_service.semantic_search")
@patch("app.services.proactive_service.get_messages_by_ids")
def test_get_proactive_suggestions_same_session_filtered(mock_get_msgs, mock_search):
    mock_search.return_value = {
        "ids": [["1", "2"]],
        "distances": [[0.1, 0.2]],
    }
    mock_get_msgs.return_value = [
        {"id": 1, "session_id": "session_1", "content": "hello there" * 5, "created_at": _old_date},
        {"id": 2, "session_id": "session_1", "content": "hi there" * 5, "created_at": _old_date},
    ]
    from app.services.proactive_service import get_proactive_suggestions
    result = get_proactive_suggestions("hello world", "session_1")
    assert result == []


@patch("app.services.proactive_service.semantic_search")
@patch("app.services.proactive_service.get_messages_by_ids")
def test_get_proactive_suggestions_with_cross_session(mock_get_msgs, mock_search):
    mock_search.return_value = {
        "ids": [["2", "3"]],
        "distances": [[0.1, 0.2]],
    }
    mock_get_msgs.return_value = [
        {"id": 2, "session_id": "session_2", "content": "different session content about coding" * 5, "created_at": _old_date},
        {"id": 3, "session_id": "session_3", "content": "another old session about python" * 5, "created_at": _old_date},
    ]
    from app.services.proactive_service import get_proactive_suggestions
    result = get_proactive_suggestions("hello world", "session_1")
    assert len(result) >= 1
    assert result[0]["session_id"] in ("session_2", "session_3")


@patch("app.services.proactive_service._generate_suggestion_narrative")
@patch("app.services.proactive_service.semantic_search")
@patch("app.services.proactive_service.get_messages_by_ids")
def test_suggestion_narrative(mock_get_msgs, mock_search, mock_narrative):
    mock_search.return_value = {
        "ids": [["2", "3"]],
        "distances": [[0.2, 0.3]],
    }
    mock_get_msgs.return_value = [
        {"id": 2, "session_id": "session_2", "content": "different session content about coding" * 5, "created_at": _old_date},
        {"id": 3, "session_id": "session_3", "content": "another session about python" * 5, "created_at": _old_date},
    ]
    mock_narrative.return_value = "This reminds me of what you said about coding earlier."
    from app.services.proactive_service import get_proactive_suggestions
    result = get_proactive_suggestions("hello world", "session_1")
    assert len(result) >= 1
