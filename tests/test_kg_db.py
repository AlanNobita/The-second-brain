"""tests/test_kg_db.py"""
import sqlite3
import pytest
from app.models.kg_db import init_kg_db, add_entity, get_all_entities, get_entity, add_relationship, get_relationship, get_all_relationships, delete_entity, delete_relationship, get_graph_data, search_entities, KG_DB_PATH


@pytest.fixture(autouse=True)
def clean_kg():
    init_kg_db()
    conn = sqlite3.connect(KG_DB_PATH)
    conn.execute("DELETE FROM relationships")
    conn.execute("DELETE FROM entities")
    conn.commit()
    conn.close()


def test_init_creates_tables():
    conn = sqlite3.connect(KG_DB_PATH)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    names = [r[0] for r in tables]
    assert "entities" in names
    assert "relationships" in names


def test_add_and_get_entity():
    eid = add_entity("Python", "language", "A programming language")
    e = get_entity(eid)
    assert e["name"] == "Python"
    assert e["type"] == "language"


def test_add_entity_dedup():
    eid1 = add_entity("Python", "language", "")
    eid2 = add_entity("Python", "framework", "")
    assert eid1 == eid2
    e = get_entity(eid1)
    assert e["type"] == "language"


def test_add_and_get_relationship():
    py = add_entity("Python", "language", "")
    fl = add_entity("Flask", "framework", "")
    rid = add_relationship(py, fl, "built with")
    r = get_relationship(rid)
    assert r["relationship_type"] == "built with"
    assert r["source_entity_id"] == py
    assert r["target_entity_id"] == fl


def test_delete_entity_cascades():
    py = add_entity("Python", "language", "")
    fl = add_entity("Flask", "framework", "")
    add_relationship(py, fl, "built with")
    delete_entity(py)
    rels = get_all_relationships()
    assert len(rels) == 0


def test_get_graph_data():
    py = add_entity("Python", "language", "Desc")
    fl = add_entity("Flask", "framework", "")
    add_relationship(py, fl, "built with")
    data = get_graph_data()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    labels = [n["label"] for n in data["nodes"]]
    assert "Python" in labels
    assert "Flask" in labels


def test_search_entities():
    add_entity("Python", "language", "")
    add_entity("PostgreSQL", "database", "")
    results = search_entities("Post")
    assert len(results) == 1
    assert results[0]["name"] == "PostgreSQL"
