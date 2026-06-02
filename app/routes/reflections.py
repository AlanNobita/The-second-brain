from flask import Blueprint, jsonify
from ..services.reflection_service import (
    get_todays_reflection,
    get_reflections_list,
    generate_daily_reflection,
)

reflection_bp = Blueprint("reflections", __name__)


@reflection_bp.route("/api/reflections", methods=["GET"])
def list_reflections():
    return jsonify(get_reflections_list())


@reflection_bp.route("/api/reflection/today", methods=["GET"])
def todays_reflection():
    ref = get_todays_reflection()
    if ref:
        return jsonify(ref)
    return jsonify(None)


@reflection_bp.route("/api/reflection/generate", methods=["POST"])
def generate_reflection():
    result = generate_daily_reflection()
    if result:
        return jsonify(result), 201
    return jsonify({"error": "No messages to reflect on today"}), 400
