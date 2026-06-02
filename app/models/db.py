import re
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "second_brain.db")

# FTS5 reserved words that, if left bare, raise "syntax error" instead of
# doing a textual search. We strip them entirely (case-insensitive). If a
# query consists only of these tokens, the sanitizer returns "" and the
# caller is expected to short-circuit.
_FTS5_RESERVED = re.compile(
    r"\b(?:AND|OR|NOT|NEAR)\b", flags=re.IGNORECASE
)

# Pattern that matches FTS5 special syntax characters we want to neutralize.
# FTS5 treats these specially: " (phrase), * (prefix), ^ (boost), - (negate),
# () (grouping), : (column filter).
_FTS5_SPECIAL = re.compile(r'["*^\-():]')

# Cap query length to avoid pathological patterns. 200 chars is well above
# any real human search query.
_FTS5_MAX_LEN = 200


def _sanitize_fts5(query: str) -> str:
    """Convert arbitrary user input into a safe FTS5 MATCH expression.

    Strategy: extract word characters, drop FTS5 reserved words, drop
    stopwords, drop noise (special chars), quote each remaining word.
    Returns "" if no usable terms survive.
    """
    if not query:
        return ""
    if len(query) > _FTS5_MAX_LEN:
        query = query[:_FTS5_MAX_LEN]
    # Strip FTS5 specials entirely - we don't support them as syntax.
    cleaned = _FTS5_SPECIAL.sub(" ", query)
    # Drop reserved words as full-word matches.
    cleaned = _FTS5_RESERVED.sub(" ", cleaned)
    # Pick out word characters (Unicode letters/digits/underscore).
    words = re.findall(r"\w+", cleaned, flags=re.UNICODE)
    if not words:
        return ""
    # Quote each term so FTS5 treats it as a literal phrase token.
    quoted = [f'"{w}"' for w in words]
    return " ".join(quoted)


def _escape_like(query: str) -> str:
    """Escape SQL LIKE wildcards in user input.

    SQLite's LIKE treats % (any) and _ (single char) as wildcards. We
    escape them with backslash and tell SQLite to use backslash as the
    ESCAPE character.
    """
    return (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys for the lifetime of this connection. Other DB
    # helpers (youtube_db, reflection_db) live in the same file, so this
    # is the only place that needs to set it for them all.
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL mode persists at the file level; setting it on every connection
    # is a cheap no-op after the first call but documents the intent.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id);
    """)
    conn.commit()
    conn.close()


def init_fts():
    conn = get_connection()
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
        USING fts5(content)
    """)
    count = conn.execute("SELECT count(*) FROM messages_fts").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO messages_fts(rowid, content) SELECT id, content FROM messages")
    # Keep FTS5 in sync with the messages table. Without these triggers,
    # deleting a message would leave its FTS row stranded, and the hybrid
    # search would return a rowid pointing at a missing parent - silent miss.
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS messages_fts_insert
        AFTER INSERT ON messages
        BEGIN
            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END;

        CREATE TRIGGER IF NOT EXISTS messages_fts_delete
        AFTER DELETE ON messages
        BEGIN
            DELETE FROM messages_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS messages_fts_update
        AFTER UPDATE ON messages
        BEGIN
            UPDATE messages_fts SET content = new.content WHERE rowid = old.id;
        END;
    """)
    conn.commit()
    conn.close()


def search_messages_fts(query, limit=20):
    if not query:
        return []
    safe = _sanitize_fts5(query)
    if not safe:
        return []
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT rowid, rank FROM messages_fts WHERE content MATCH ? ORDER BY rank LIMIT ?",
            (safe, limit)
        ).fetchall()
        return [(r["rowid"], r["rank"]) for r in rows]
    except sqlite3.OperationalError as e:
        logger.warning("FTS5 query failed (returning []): %s | original=%r sanitized=%r", e, query, safe)
        return []
    finally:
        conn.close()


def save_message(session_id, role, content):
    # Hardening: enforce that the role/session_id is a non-empty string and
    # the content is a string (empty allowed - the LLM may legitimately
    # return ""). Rejecting None / non-string prevents the
    # ``NOT NULL constraint failed: messages.content`` 500 that would
    # otherwise leak to the client.
    if not isinstance(content, str):
        raise ValueError(f"save_message: content must be a string, got {content!r}")
    if not isinstance(role, str) or not role:
        raise ValueError(f"save_message: role must be a non-empty string, got {role!r}")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError(f"save_message: session_id must be a non-empty string, got {session_id!r}")
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?,?,?)",
        (session_id, role, content)
    )
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return message_id


def get_message(session_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_sessions():
    """Returns a list of distinct sessions with their first message and timestamp"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT session_id,
        MIN(created_at) AS created_at,
        COUNT(*) AS message_count,
        (
            SELECT content FROM messages
            WHERE session_id = m.session_id AND role = 'user'
            ORDER BY created_at ASC LIMIT 1
        ) AS title
        FROM messages AS m
        GROUP BY session_id
        Order BY created_at DESC"""
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]



def search_messages(query):
    """LIKE-based keyword search. Wildcards in user input are escaped."""
    if not query:
        return []
    safe = _escape_like(query)
    conn = get_connection()
    rows = conn.execute(
        "SELECT content, role, session_id, created_at FROM messages "
        "WHERE content LIKE ? ESCAPE '\\' ORDER BY created_at DESC LIMIT 50",
        (f"%{safe}%",)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_messages_by_ids(message_ids):
    """Takes a list of message ids and returns the full message dicts in input order."""
    if not message_ids:
        return []
    # Dedupe IDs while preserving order to avoid returning the same row twice.
    seen = set()
    unique_ids = []
    for mid in message_ids:
        if mid in seen:
            continue
        seen.add(mid)
        unique_ids.append(mid)
    placeholders = ",".join("?" * len(unique_ids))
    conn = get_connection()
    rows = conn.execute(
        f"SELECT * FROM messages WHERE id IN ({placeholders})", unique_ids
    ).fetchall()
    conn.close()

    messages = {row["id"]: dict(row) for row in rows}
    return [messages[id_] for id_ in unique_ids if id_ in messages]


def delete_session(session_id):
    """Delete all messages associated with a session_id from the database."""
    conn = get_connection()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
