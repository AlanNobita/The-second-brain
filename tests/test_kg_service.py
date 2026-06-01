"""tests/test_kg_service.py"""
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


def test_create_and_list():
    from app.services.kg_service import create_entity, list_entities
    e = create_entity("Python", "language")
    assert e["name"] == "Python"
    all_e = list_entities()
    assert len(all_e) == 1


def test_create_relationship():
    from app.services.kg_service import create_entity, create_relationship, list_relationships
    py = create_entity("Python", "language")
    fl = create_entity("Flask", "framework")
    r = create_relationship(py["id"], fl["id"], "built with")
    assert r["relationship_type"] == "built with"
    assert len(list_relationships()) == 1


def test_extract_triples_creates_entities_and_relationships():
    from app.services.kg_service import extract_triples, list_entities, list_relationships
    result = extract_triples([("Python", "built with", "Flask")])
    assert result["relationships_created"] == 1
    assert len(list_entities()) == 2
    assert len(list_relationships()) == 1


def test_extract_triples_dedup():
    from app.services.kg_service import extract_triples, list_entities, list_relationships
    extract_triples([("Python", "built with", "Flask")])
    extract_triples([("Python", "built with", "Flask")])
    entities = list_entities()
    assert len(entities) == 2
    assert len(list_relationships()) == 2


def test_delete_via_service():
    from app.services.kg_service import create_entity, delete_entity, list_entities
    e = create_entity("Temp", "test")
    assert len(list_entities()) == 1
    delete_entity(e["id"])
    assert len(list_entities()) == 0


def test_get_graph_data():
    from app.services.kg_service import create_entity, create_relationship, get_graph_data
    py = create_entity("Python", "language")
    fl = create_entity("Flask", "framework")
    create_relationship(py["id"], fl["id"], "built with")
    data = get_graph_data()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1


def test_get_entity_by_id():
    from app.services.kg_service import create_entity, get_entity_by_id
    e = create_entity("Python", "language")
    found = get_entity_by_id(e["id"])
    assert found["name"] == "Python"
    assert get_entity_by_id(99999) is None


def test_delete_relationship():
    from app.services.kg_service import create_entity, create_relationship, list_relationships, delete_relationship
    py = create_entity("Python", "language")
    fl = create_entity("Flask", "framework")
    r = create_relationship(py["id"], fl["id"], "built with")
    assert len(list_relationships()) == 1
    delete_relationship(r["id"])
    assert len(list_relationships()) == 0


def test_search_entities():
    from app.services.kg_service import create_entity, search_entities
    create_entity("Python", "language")
    create_entity("PostgreSQL", "database")
    results = search_entities("Post")
    assert len(results) == 1
    assert results[0]["name"] == "PostgreSQL"
