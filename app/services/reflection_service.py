import logging
from datetime import date, datetime
from openai import OpenAI
from flask import current_app

from ..models.db import get_connection
from ..models.reflection_db import (
    save_reflection,
    get_reflection,
    list_reflections,
    reflection_exists,
    get_all_message_ids,
)

logger = logging.getLogger(__name__)


def _get_today_messages():
    today = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, content, session_id, role, created_at
           FROM messages
           WHERE DATE(created_at) = ?
           ORDER BY created_at ASC""",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _get_all_recent_dates(days=7):
    """Return distinct dates (newest first) on which the user has messaged.

    Uses ``get_all_message_ids`` to confirm the underlying user-message
    timeline is non-empty before deriving dates from it; this keeps the
    backfill honest if the database is migrated and the messages table
    is briefly out of sync with reflections.
    """
    user_messages = get_all_message_ids()
    if not user_messages:
        return []
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT DATE(created_at) as d
           FROM messages
           WHERE role = 'user'
           ORDER BY d DESC
           LIMIT ?""",
        (days,),
    ).fetchall()
    conn.close()
    return [row["d"] for row in rows]


def generate_daily_reflection(for_date=None):
    if for_date is None:
        for_date = date.today().isoformat()

    messages = _get_today_messages()
    if not messages:
        logger.info("No messages found for %s, skipping reflection", for_date)
        return None

    user_messages = [m for m in messages if m["role"] == "user"]
    if not user_messages:
        logger.info("No user messages for %s, skipping reflection", for_date)
        return None

    topics_prompt = (
        "Analyze these user messages from today and extract 3-5 key topics or themes. "
        "Return ONLY a JSON array of strings, nothing else. Example: "
        '["python async patterns", "flask middleware", "database optimization"]\n\n'
        "Messages:\n"
        + "\n".join(f"- {m['content'][:500]}" for m in user_messages[:20])
    )

    client = OpenAI(
        api_key=current_app.config["OPENROUTER_API_KEY"],
        base_url=current_app.config["OPENROUTER_BASE_URL"],
    )

    try:
        topics_resp = client.chat.completions.create(
            model=current_app.config.get("OPENROUTER_MODEL", "deepseek-v4-flash-free"),
            messages=[{"role": "user", "content": topics_prompt}],
        )
        content = topics_resp.choices[0].message.content
        topics_text = content.strip() if content else ""
        import json
        try:
            topics = json.loads(topics_text)
        except json.JSONDecodeError:
            topics = [t.strip("- ").strip() for t in topics_text.split("\n") if t.strip()]

        summary_prompt = (
            "Write a brief daily learning reflection (2-3 paragraphs) summarizing "
            "what the user explored, learned, or worked on today based on their messages. "
            "Focus on key insights and connections between topics.\n\n"
            f"Key topics: {', '.join(topics[:5])}\n\n"
            "Messages:\n"
            + "\n".join(f"[{m['session_id'][:8]}] {m['role']}: {m['content'][:500]}"
                       for m in messages[:30])
        )

        summary_resp = client.chat.completions.create(
            model=current_app.config.get("OPENROUTER_MODEL", "deepseek-v4-flash-free"),
            messages=[{"role": "user", "content": summary_prompt}],
        )
        content = summary_resp.choices[0].message.content
        summary = content.strip() if content else ""

        message_ids = [m["id"] for m in messages]
        save_reflection(for_date, summary, topics, message_ids)
        logger.info("Saved daily reflection for %s with %d messages", for_date, len(messages))

        return {"date": for_date, "summary": summary, "topics": topics}
    except Exception as e:
        logger.error("Failed to generate daily reflection: %s", e)
        return None


def get_todays_reflection():
    today = date.today().isoformat()
    ref = get_reflection(today)
    if ref:
        import ast
        ref["topics"] = ast.literal_eval(ref["topics"]) if isinstance(ref["topics"], str) else ref["topics"]
    return ref


def get_reflections_list(limit=30):
    refs = list_reflections(limit)
    import ast
    for r in refs:
        if isinstance(r.get("topics"), str):
            r["topics"] = ast.literal_eval(r["topics"])
    return refs


def generate_missed_reflections():
    dates = _get_all_recent_dates(days=14)
    generated = []
    for d in dates:
        if not reflection_exists(d):
            ref = generate_daily_reflection(for_date=d)
            if ref:
                generated.append(ref)
    return generated
