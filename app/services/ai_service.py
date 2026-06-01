from openai import OpenAI
from flask import current_app
# from .memory_service import get_or_create_session
from ..models.db import save_message, get_message
from .embedding_service import store_embedding

def get_ai_response(session_id, user_message):
    # Save user message
    # save_message(session_id, "user", user_message)
    msg_id = save_message(session_id=session_id, role="user", content=user_message)
    store_embedding(message_id=msg_id, session_id=session_id, text=user_message, role="user")

    #build conversation history for context
    history = get_message(session_id)

    #format for openrouter
    messages = [
        {
            "role": m["role"], "content": m["content"]
        } for m in history
    ]

    # Call the AI 
    client = OpenAI(
        api_key=current_app.config["OPENROUTER_API_KEY"],
        base_url=current_app.config["OPENROUTER_BASE_URL"],
    )
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b:free",
        messages=messages #type: ignore
    )
    ai_content = response.choices[0].message.content

    # Save AI response
    # save_message(session_id, "assistant", ai_content)
    msg_id= save_message(session_id=session_id, role="assistant", content=ai_content)
    store_embedding(message_id=msg_id, text=ai_content, session_id=session_id, role="assistant")
    return ai_content