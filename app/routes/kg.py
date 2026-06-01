from flask import Blueprint, jsonify, request, render_template
from ..services.kg_service import (
    create_entity, list_entities, get_entity_by_id, delete_entity,
    create_relationship, list_relationships, delete_relationship,
    extract_triples, get_graph_data, search_entities,
    _parse_triples_from_text,
)

kg_bp = Blueprint("kg", __name__)


@kg_bp.route("/kg/graph")
def graph_data():
    q = request.args.get("q")
    if q:
        entities = search_entities(q)
        if entities:
            eid = entities[0]["id"]
            nodes = [{"id": e["id"], "label": e["name"], "title": e["type"], "description": e["description"]} for e in list_entities()]
            edges = [{"from": r["source_entity_id"], "to": r["target_entity_id"], "label": r["relationship_type"], "value": r["weight"]} for r in list_relationships()]
            return jsonify({"nodes": nodes, "edges": edges, "focus_id": eid})
    return jsonify(get_graph_data())


@kg_bp.route("/kg/entity", methods=["POST"])
def create_entity_route():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    entity = create_entity(
        name=data["name"],
        type=data.get("type", "concept"),
        description=data.get("description", ""),
    )
    return jsonify(entity), 201


@kg_bp.route("/kg/entity/<int:entity_id>", methods=["GET"])
def get_entity_route(entity_id):
    entity = get_entity_by_id(entity_id)
    if not entity:
        return jsonify({"error": "not found"}), 404
    return jsonify(entity)


@kg_bp.route("/kg/entity/<int:entity_id>", methods=["DELETE"])
def delete_entity_route(entity_id):
    delete_entity(entity_id)
    return jsonify({"status": "ok"})


@kg_bp.route("/kg/relation", methods=["POST"])
def create_relation_route():
    data = request.get_json()
    source_name = data.get("source_name") or data.get("source")
    target_name = data.get("target_name") or data.get("target")
    if not source_name or not target_name:
        return jsonify({"error": "source_name and target_name required"}), 400
    s = create_entity(source_name)
    t = create_entity(target_name)
    rel = create_relationship(
        s["id"], t["id"],
        data.get("relationship_type", "related to"),
        data.get("weight", 1.0),
    )
    return jsonify(rel), 201


@kg_bp.route("/kg/relation/<int:rel_id>", methods=["DELETE"])
def delete_relation_route(rel_id):
    delete_relationship(rel_id)
    return jsonify({"status": "ok"})


@kg_bp.route("/kg/extract", methods=["POST"])
def extract_route():
    data = request.get_json()
    triples = []
    if "triples" in data:
        triples = data["triples"]
    elif "text" in data:
        triples = _parse_triples_from_text(data["text"])
    result = extract_triples(triples)
    return jsonify(result), 201


@kg_bp.route("/kg/entities")
def list_entities_route():
    return jsonify(list_entities())


@kg_bp.route("/graph")
def graph_page():
    return render_template("graph.html")
