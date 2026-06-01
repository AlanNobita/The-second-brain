import re

from ..models.kg_db import (
    add_entity, get_entity, get_all_entities,
    delete_entity as db_delete_entity,
    add_relationship, get_relationship, get_all_relationships,
    delete_relationship as db_delete_relationship,
    get_graph_data as db_get_graph_data,
    search_entities as db_search_entities,
)


def _parse_triples_from_text(text):
    triples = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            triples.append((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            triples.append((parts[0], "related to", parts[1]))
        else:
            m = re.match(r"(.+?)\s+is\s+a\s+type\s+of\s+(.+)", line, re.IGNORECASE)
            if m:
                triples.append((m.group(1).strip(), "type of", m.group(2).strip()))
                continue
            m = re.match(r"(.+?)\s+relates\s+to\s+(.+)", line, re.IGNORECASE)
            if m:
                triples.append((m.group(1).strip(), "related to", m.group(2).strip()))
                continue
            m = re.match(r"(.+?)\s+is\s+a\s+(.+)", line, re.IGNORECASE)
            if m:
                triples.append((m.group(1).strip(), "is a", m.group(2).strip()))
                continue
    return triples


def create_entity(name, type="concept", description=""):
    eid = add_entity(name, type, description)
    return get_entity(eid)


def list_entities():
    return get_all_entities()


def get_entity_by_id(entity_id):
    return get_entity(entity_id)


def delete_entity(entity_id):
    return db_delete_entity(entity_id)


def create_relationship(source_id, target_id, rel_type, weight=1.0):
    rid = add_relationship(source_id, target_id, rel_type, weight)
    return get_relationship(rid)


def list_relationships():
    return get_all_relationships()


def delete_relationship(rel_id):
    return db_delete_relationship(rel_id)


def extract_triples(triples):
    before = set(e["name"] for e in get_all_entities())
    for source_name, rel_type, target_name in triples:
        s = create_entity(source_name.strip())
        t = create_entity(target_name.strip())
        create_relationship(s["id"], t["id"], rel_type.strip())
    after = set(e["name"] for e in get_all_entities())
    entities_created = len(after - before)
    return {"entities_created": entities_created, "relationships_created": len(triples)}


def get_graph_data():
    return db_get_graph_data()


def search_entities(q):
    return db_search_entities(q)
