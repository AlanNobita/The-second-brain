"""tests/test_kg_routes.py"""
import sqlite3
import pytest
from app.models.kg_db import KG_DB_PATH, init_kg_db


@pytest.fixture(autouse=True)
def clean_kg():
    init_kg_db()
    conn = sqlite3.connect(KG_DB_PATH)
    conn.execute("DELETE FROM relationships")
    conn.execute("DELETE FROM entities")
    conn.commit()
    conn.close()


def test_get_graph_empty(client):
    resp = client.get("/kg/graph")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "nodes" in data
    assert "edges" in data


def test_create_entity(client):
    resp = client.post("/kg/entity", json={"name": "Python", "type": "language"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Python"


def test_create_relationship(client):
    client.post("/kg/entity", json={"name": "Python", "type": "language"})
    client.post("/kg/entity", json={"name": "Flask", "type": "framework"})
    resp = client.post("/kg/relation", json={
        "source_name": "Python", "target_name": "Flask", "relationship_type": "built with"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["relationship_type"] == "built with"


def test_extract_triples(client):
    resp = client.post("/kg/extract", json={
        "triples": [("Python", "built with", "Flask")]
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["relationships_created"] == 1


def test_delete_entity(client):
    resp = client.post("/kg/entity", json={"name": "Temp", "type": "test"})
    eid = resp.get_json()["id"]
    resp = client.delete(f"/kg/entity/{eid}")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
