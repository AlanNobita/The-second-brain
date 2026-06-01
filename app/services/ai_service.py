from openai import OpenAI
from flask import current_app
# from .memory_service import get_or_create_session
from ..models.db import save_message, get_message
from .embedding_service import store_embedding
from .embedding_service import semantic_search
from ..models.db import get_messages_by_ids
from threading import Thread
import logging

logger = logging.getLogger(__name__)

def _lazy_youtube_check():
    try:
        from .subscription_service import check_due_subscriptions
        result = check_due_subscriptions()
        if result and result.get("ingested_count", 0) > 0:
            logger.info("Lazy YouTube check ingested %s videos", result["ingested_count"])
    except Exception as e:
        logger.debug("Lazy YouTube check skipped: %s", e)

def get_ai_response(session_id, user_message):
    # Lazy YouTube check in background
    Thread(target=_lazy_youtube_check, daemon=True).start()

    # Save user message
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

    rag_results = semantic_search(user_message, limit= 3)
    rag_ids = [int(id_) for id_ in rag_results["ids"][0]]
    rag_messages = get_messages_by_ids(rag_ids)
    rag_messages = [m for m in rag_messages if m["session_id"] != session_id]

    if rag_messages: 
        rag_content = "\n\n".join(
            f"[Previous conversation - {m["session_id"][:8]}...] {m["role"]}: {m["content"]}" for m in rag_messages[:3]
        )   
        
        system_prompt = {
            "role": "system", 
            "content": (
                "You are a Second Brain AI assistant. "
                "Here are relevant past messages from the user's history: \n\n"
                f"{rag_content}"
                "Use them for context when answering the current question."
            )
        }
        messages.insert(0, system_prompt)
        
        # Call the AI 
    client = OpenAI(
        api_key=current_app.config["OPENROUTER_API_KEY"],
        base_url=current_app.config["OPENROUTER_BASE_URL"],
    )
    response = client.chat.completions.create(
        model=current_app.config.get("OPENROUTER_MODEL", "deepseek-v4-flash-free"),
        messages=messages #type: ignore
    )
    ai_content = response.choices[0].message.content

    # Save AI response
    # save_message(session_id, "assistant", ai_content)
    msg_id= save_message(session_id=session_id, role="assistant", content=ai_content)
    store_embedding(message_id=msg_id, text=ai_content, session_id=session_id, role="assistant")
    return ai_content