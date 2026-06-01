-- Cognitive Operating System - Database Schema
-- SQLite3

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    session_id TEXT NOT NULL, 
    role TEXT NOT NULL, 
    content TEXT NOT NULL, 
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index for faster session lookups 
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
