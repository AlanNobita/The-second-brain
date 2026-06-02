import logging

from ..models.db import get_connection

logger = logging.getLogger(__name__)


def get_or_create_session(session_id):
    """Return whether a session_id is new or already known.

    Checks the `messages` table for any row with the given `session_id`.
    Returns ``{"session_id": session_id, "created": False}`` when the
    session already exists, and ``{"session_id": session_id, "created": True}``
    when it does not (caller is responsible for inserting the first message
    that marks the session as started).

    Raises ``ValueError`` if ``session_id`` is not a non-empty string.
    """
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("session_id must be a non-empty string")

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()

    return {"session_id": session_id, "created": row is None}
