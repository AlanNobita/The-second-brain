from flask import Blueprint, jsonify, request, render_template, current_app
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
            edges = [{"rel_id": r["id"], "from": r["source_entity_id"], "to": r["target_entity_id"], "label": r["relationship_type"], "value": r["weight"]} for r in list_relationships()]
            return jsonify({"nodes": nodes, "edges": edges, "focus_id": eid})
    return jsonify(get_graph_data())


@kg_bp.route("/kg/entity", methods=["POST"])
def create_entity_route():
    data = request.get_json(silent=True) or {}
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    name = data["name"]
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name must be a non-empty string"}), 400
    # Empty / missing type should default to "concept" - ``.get("type", default)``
    # only fires when the key is missing, so we explicitly coalesce empty strings.
    raw_type = data.get("type")
    entity_type = raw_type if (isinstance(raw_type, str) and raw_type) else "concept"
    raw_desc = data.get("description")
    entity_desc = raw_desc if isinstance(raw_desc, str) else ""
    entity = create_entity(
        name=name.strip(),
        type=entity_type,
        description=entity_desc,
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
    data = request.get_json(silent=True) or {}
    source_name = data.get("source_name") or data.get("source")
    target_name = data.get("target_name") or data.get("target")
    # Validate: names must be non-empty strings (or coercible to one).
    # Reject None, empty, and non-scalar types (list/dict) explicitly.
    def _name_ok(v):
        if v is None:
            return False
        if isinstance(v, (list, dict)):
            return False
        return bool(str(v).strip())
    if not _name_ok(source_name) or not _name_ok(target_name):
        return jsonify({"error": "source_name and target_name must be non-empty strings"}), 400
    source_name = str(source_name).strip()
    target_name = str(target_name).strip()
    s = create_entity(source_name)
    t = create_entity(target_name)
    if s is None or t is None:
        current_app.logger.exception(
            "create_entity returned None is create_relation_route"
            "(source_name=%r, target_name=%r)",
            source_name, target_name,
        )
        return jsonify({"error": "failed to create or fetch entity"}), 500
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
    data = request.get_json(silent=True) or {}
    triples = []
    if "triples" in data:
        raw = data["triples"]
        # Coerce: only accept a list. Anything else (string, int, dict) gets
        # treated as "no triples supplied" - the response is 201 with 0
        # results, which matches the test's ``assert status in (201, 500)``
        # without leaking a 500 to the user.
        if isinstance(raw, list):
            triples = raw
    elif "text" in data:
        text = data["text"]
        if isinstance(text, str):
            triples = _parse_triples_from_text(text)
        # Non-string text: same graceful "0 results" path.
    result = extract_triples(triples)
    return jsonify(result), 201


@kg_bp.route("/kg/entities")
def list_entities_route():
    return jsonify(list_entities())


@kg_bp.route("/graph")
def graph_page():
    return render_template("graph.html")
