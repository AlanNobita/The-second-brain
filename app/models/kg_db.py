import sqlite3
import os

KG_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "second_brain.db")


def _get_conn():
    conn = sqlite3.connect(KG_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_kg_db():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL DEFAULT 'concept',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                relationship_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_entity_id);
            CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_entity_id);
        """)
        conn.commit()
    finally:
        conn.close()


def add_entity(name, type="concept", description=""):
    conn = _get_conn()
    try:
        try:
            cur = conn.execute("INSERT INTO entities (name, type, description) VALUES (?, ?, ?)", (name, type, description))
            conn.commit()
            eid = cur.lastrowid
        except sqlite3.IntegrityError:
            row = conn.execute("SELECT id FROM entities WHERE name = ?", (name,)).fetchone()
            eid = row["id"]
    finally:
        conn.close()
    return eid


def get_entity(entity_id):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def get_all_entities():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM entities ORDER BY name").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def delete_entity(entity_id):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        conn.commit()
    finally:
        conn.close()


def add_relationship(source_entity_id, target_entity_id, relationship_type, weight=1.0):
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO relationships (source_entity_id, target_entity_id, relationship_type, weight) VALUES (?, ?, ?, ?)",
            (source_entity_id, target_entity_id, relationship_type, weight)
        )
        conn.commit()
        rid = cur.lastrowid
    finally:
        conn.close()
    return rid


def get_relationship(rel_id):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM relationships WHERE id = ?", (rel_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def get_all_relationships():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM relationships").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def delete_relationship(rel_id):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM relationships WHERE id = ?", (rel_id,))
        conn.commit()
    finally:
        conn.close()


def get_graph_data():
    entities = get_all_entities()
    rels = get_all_relationships()
    nodes = [{"id": e["id"], "label": e["name"], "title": e["type"], "description": e["description"]} for e in entities]
    edges = [{"from": r["source_entity_id"], "to": r["target_entity_id"], "label": r["relationship_type"], "value": r["weight"]} for r in rels]
    return {"nodes": nodes, "edges": edges}


def search_entities(q):
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM entities WHERE name LIKE ?", (f"%{q}%",)).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
