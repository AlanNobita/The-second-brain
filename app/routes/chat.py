from flask import Blueprint
from flask import jsonify, request, send_from_directory
import os
import logging
from ..services.ai_service import get_ai_response
from uuid import uuid4
from ..models.db import get_sessions, get_message
from ..models.db import get_messages_by_ids

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/")
def index():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    return send_from_directory(static_dir, "index.html")

@chat_bp.route("/chat/send", methods=["POST"])
def send_message():
    data = request.get_json(silent=True) or {}

    # Coerce message to a string. None, missing, or empty all become "" so
    # the LLM gets a sensible input (and the test that asserts 200 on
    # {"message": ""} passes). Lists/dicts are rejected with 400 - they
    # can't be coerced to text meaningfully. Booleans are rejected because
    # ``str(True) == "True"`` would be a confusing message.
    raw_message = data.get("message")
    if raw_message is None:
        user_message = ""
    elif isinstance(raw_message, (list, dict)):
        return jsonify({"error": "message must be a string, not a list or object"}), 400
    elif isinstance(raw_message, bool):
        return jsonify({"error": "message must be a string, not a boolean"}), 400
    elif not isinstance(raw_message, str):
        # Numbers (int/float) coerce to text.
        user_message = str(raw_message)
    else:
        user_message = raw_message

    if len(user_message) > 200000:
        return jsonify({"error": "message too long (max 200000 chars)"}), 413

    session_id = data.get("session_id") or str(uuid4())

    ai_reply, suggestion, sources = get_ai_response(session_id, user_message)

    resp = {
        "session_id": session_id,
        "reply": ai_reply,
    }
    if suggestion:
        resp["suggestion"] = suggestion
    if sources:
        resp["sources"] = sources

    return jsonify(resp)

@chat_bp.route("/sessions", methods=["GET"])
def show_sessions():
    """Calls get_sessions() and returns JSON"""
    """we already have all the list of sessions there from the database through get_sessions, here we just need to call the functiona nd return if as a json"""
    return jsonify(get_sessions())
     # Return jsonify(get_sessions)

@chat_bp.route("/chat/history", methods = ["GET"])
def show_session_messages():
    """
    accepts get requests at /chat/history
    reads session_id from the URL query string (not from json body - it iis a get, no post)
    flask has reques.args.get("sessions_id") for quey parameter
    calls get_message(session_id) fromm the database
    returns json of the stored messages"""
    session_id = request.args.get("session_id", default="")

    # put and error handling mechanism in case the session id is not available
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    
    messages = get_message(session_id=session_id)

    return jsonify({"session_id": session_id, "messages": messages})


@chat_bp.route("/search", methods=["GET"])
def find_message_with_keywords():
    query = request.args.get("q", "")
    mode = request.args.get("mode", "hybrid")

    if not query or not query.strip():
        return jsonify([])

    if mode == "semantic":
        from ..services.embedding_service import semantic_search as vec_search
        results = vec_search(query)
        message_ids = [int(id_) for id_ in results["ids"][0]]
        messages = get_messages_by_ids(message_ids)
        for m in messages:
            m["_source"] = "semantic"
            m["_score"] = 0
        return jsonify(messages)

    from ..services.hybrid_search import search as hybrid_search
    return jsonify(hybrid_search(query, mode=mode))


@chat_bp.route("/session/<session_id>", methods=["DELETE"])
def delete_session_route(session_id):
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # Delete from SQLite database
    from ..models.db import delete_session
    delete_session(session_id)

    # Delete from ChromaDB
    from ..services.embedding_service import delete_session_embeddings
    try:
        delete_session_embeddings(session_id)
    except Exception as e:
        logging.getLogger(__name__).warning("Failed to delete embeddings for session %s: %s", session_id, e)

    return jsonify({"status": "ok"})