from flask import Blueprint
from flask import jsonify, request
from ..services.ai_service import get_ai_response
from uuid import uuid4

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/")
def index():
    return "Hello from the Second brain"

@chat_bp.route("/chat/send", methods=["POST"])
def send_message():
    data = request.get_json()
    
    user_message = data.get("message", "")
    session_id = data.get("session_id") or str(uuid4())

    ai_reply = get_ai_response(session_id, user_message)

    return jsonify(
        {
            "session_id": session_id,  
            "reply": ai_reply
        }
    )