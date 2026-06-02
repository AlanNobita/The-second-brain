import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "second_brain.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_reflection_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_reflections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL UNIQUE,
            summary     TEXT    NOT NULL,
            topics      TEXT    NOT NULL DEFAULT '[]',
            message_ids TEXT    NOT NULL DEFAULT '[]',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Reflection database initialized")


def save_reflection(date, summary, topics=None, message_ids=None):
    if topics is None:
        topics = []
    if message_ids is None:
        message_ids = []
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO daily_reflections (date, summary, topics, message_ids)
           VALUES (?, ?, ?, ?)""",
        (date, summary, str(topics), str(message_ids)),
    )
    conn.commit()
    conn.close()


def get_reflection(date):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM daily_reflections WHERE date = ?", (date,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_reflections(limit=30):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM daily_reflections ORDER BY date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def reflection_exists(date):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM daily_reflections WHERE date = ?", (date,)
    ).fetchone()
    conn.close()
    return row is not None


def get_all_message_ids():
    """Return ``{id, created_at}`` for every user message in `messages`.

    Lives in the reflection module because the reflection pipeline is the
    primary consumer (it cross-references user activity across days), but
    it can also be used by any code that needs the full user-message
    timeline.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, created_at FROM messages WHERE role = 'user' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
