from ..models.kg_db import (
    add_entity, get_entity, get_all_entities,
    delete_entity as db_delete_entity,
    add_relationship, get_relationship, get_all_relationships,
    delete_relationship as db_delete_relationship,
    get_graph_data as db_get_graph_data,
    search_entities as db_search_entities,
)


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
    for source_name, rel_type, target_name in triples:
        s = add_entity(source_name.strip())
        t = add_entity(target_name.strip())
        add_relationship(s, t, rel_type.strip())
    return {"relationships_created": len(triples)}


def get_graph_data():
    return db_get_graph_data()


def search_entities(q):
    return db_search_entities(q)
