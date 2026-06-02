import logging
from datetime import datetime, timedelta
from openai import OpenAI
from flask import current_app

from .embedding_service import semantic_search
from ..models.db import get_messages_by_ids

logger = logging.getLogger(__name__)


def get_proactive_suggestions(user_message, current_session_id, limit=3):
    try:
        similar = semantic_search(user_message, limit=10)
        ids = [int(id_) for id_ in similar["ids"][0]]
        distances = similar["distances"][0] if similar.get("distances") else [0] * len(ids)

        messages = get_messages_by_ids(ids)
        relevant = []
        for m, dist in zip(messages, distances):
            if m["session_id"] != current_session_id and len(m["content"]) > 20:
                m["_distance"] = dist
                relevant.append(m)

        if len(relevant) < 2:
            return []

        recent_cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        old_relevant = [m for m in relevant if str(m.get("created_at", "")) < recent_cutoff]

        if not old_relevant:
            return []

        context_items = old_relevant[:limit]
        suggestions = []
        for m in context_items:
            preview = m["content"][:120]
            sid_preview = m["session_id"][:8]
            suggestions.append({
                "session_id": m["session_id"],
                "preview": preview,
                "from_session": sid_preview,
            })

        return suggestions
    except Exception as e:
        logger.debug("Proactive suggestion check failed: %s", e)
        return []


def _generate_suggestion_narrative(user_message, suggestions):
    if not suggestions:
        return None
    client = OpenAI(
        api_key=current_app.config["OPENROUTER_API_KEY"],
        base_url=current_app.config["OPENROUTER_BASE_URL"],
    )
    prompt = (
        "You are a proactive note-taking assistant. The user just said something. "
        "Below are past messages from the user that are semantically related. "
        "Write ONE short sentence (max 30 words) connecting the current message "
        "to the past one. Be casual and insightful, like 'reminds me of...'\n\n"
        f"Current: {user_message}\n\n"
        f"Past: {' | '.join(s['preview'] for s in suggestions[:2])}"
    )
    try:
        resp = client.chat.completions.create(
            model=current_app.config.get("OPENROUTER_MODEL", "deepseek-v4-flash-free"),
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.debug("Suggestion narrative failed: %s", e)
        return None
