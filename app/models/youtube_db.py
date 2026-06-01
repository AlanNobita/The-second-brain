import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "second_brain.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_youtube_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_url  TEXT    NOT NULL UNIQUE,
            channel_name TEXT    NOT NULL,
            last_checked TEXT,
            fail_count   INTEGER NOT NULL DEFAULT 0,
            active       INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS ingested_videos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id     TEXT    NOT NULL UNIQUE,
            channel_name TEXT    NOT NULL,
            video_title  TEXT    NOT NULL,
            video_url    TEXT    NOT NULL,
            ingested_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            session_id   TEXT    NOT NULL,
            file_path    TEXT
        );
    """)
    conn.commit()
    conn.close()

def add_subscription(channel_url, channel_name):
    conn = _get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO subscriptions (channel_url, channel_name) VALUES (?, ?)",
        (channel_url, channel_name)
    )
    conn.execute(
        "UPDATE subscriptions SET active = 1, fail_count = 0 WHERE channel_url = ?",
        (channel_url,)
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE channel_url = ?", (channel_url,)
    ).fetchone()
    conn.close()
    return dict(row)

def get_subscription(sub_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE id = ?", (sub_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_subscriptions(only_active=True):
    conn = _get_conn()
    if only_active:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE active = 1 ORDER BY channel_name"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM subscriptions ORDER BY channel_name"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def remove_subscription(sub_id):
    conn = _get_conn()
    cursor = conn.execute("UPDATE subscriptions SET active = 0 WHERE id = ?", (sub_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def update_last_checked(sub_id):
    conn = _get_conn()
    conn.execute(
        "UPDATE subscriptions SET last_checked = datetime('now'), fail_count = 0 WHERE id = ?",
        (sub_id,)
    )
    conn.commit()
    conn.close()

def mark_subscription_inactive(sub_id):
    remove_subscription(sub_id)

def add_ingested_video(video_id, channel_name, video_title, video_url, session_id, file_path=None):
    conn = _get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO ingested_videos
           (video_id, channel_name, video_title, video_url, session_id, file_path)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (video_id, channel_name, video_title, video_url, session_id, file_path)
    )
    conn.commit()
    conn.close()

def is_video_ingested(video_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM ingested_videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    conn.close()
    return row is not None

def get_ingested_videos(limit=50):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM ingested_videos ORDER BY ingested_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
