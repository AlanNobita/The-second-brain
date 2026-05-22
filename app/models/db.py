import sqlite3
import os 

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "second_brain.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def save_message(session_id, role, content):
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
