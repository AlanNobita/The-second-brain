from openai import OpenAI
from flask import current_app
# from .memory_service import get_or_create_session
from ..models.db import save_message, get_message
from .embedding_service import store_embedding
from .embedding_service import semantic_search
from ..models.db import get_messages_by_ids
from .proactive_service import get_proactive_suggestions, _generate_suggestion_narrative
from threading import Thread
import logging
import re

logger = logging.getLogger(__name__)

_YT_TITLE_RE = re.compile(r"^\[YouTube\]\s+(.+?)\s+\(\d+/\d+\)$")


def _classify_source(session_id: str, content_prefix: str) -> str:
    """Classify a RAG chunk as either 'youtube' or 'chat' based on session_id and prefix."""
    if session_id.startswith("yt_"):
        return "youtube"
    if content_prefix.startswith("[YouTube]"):
        return "youtube"
    return "chat"


def _extract_yt_title(content: str) -> str | None:
    """Extract the YouTube video title from a chunk's prefix, if present."""
    first_line = content.split("\n", 1)[0]
    m = _YT_TITLE_RE.match(first_line.strip())
    if m:
        return m.group(1)
    return None


def _resolve_yt_url(session_id: str) -> str | None:
    """Look up the YouTube URL for a given yt_* session_id from ingested_videos."""
    try:
        from ..models.youtube_db import get_ingested_videos
        ingested = get_ingested_videos(limit=1000)
        for row in ingested:
            if row["session_id"] == session_id:
                return row["video_url"]
    except Exception as e:
        logger.debug("Could not resolve YT url for %s: %s", session_id, e)
    return None


def _youtube_search_url(title: str) -> str:
    """Fallback URL: a YouTube search for the title."""
    from urllib.parse import quote_plus
    return f"https://www.youtube.com/results?search_query={quote_plus(title)}"


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

    rag_results = semantic_search(user_message, limit=30)
    rag_ids = [int(id_) for id_ in rag_results["ids"][0]]
    rag_messages = get_messages_by_ids(rag_ids)
    rag_messages = [m for m in rag_messages if m["session_id"] != session_id]

    seen = set()
    deduped = []
    for m in rag_messages:
        if m["id"] in seen:
            continue
        deduped.append(m)
        seen.add(m["id"])
    rag_messages = deduped

    yt_in_candidates = [m for m in rag_messages if _classify_source(m["session_id"], m["content"]) == "youtube"]
    yt_in_top3 = [m for m in rag_messages[:3] if _classify_source(m["session_id"], m["content"]) == "youtube"]
    if yt_in_candidates and len(yt_in_top3) < 2:
        for yt in yt_in_candidates:
            if any(m["id"] == yt["id"] for m in rag_messages[:3]):
                continue
            for i in range(2, -1, -1):
                m = rag_messages[i]
                if _classify_source(m["session_id"], m["content"]) == "chat":
                    rag_messages[i] = yt
                    break
            else:
                continue
            if len([m for m in rag_messages[:3] if _classify_source(m["session_id"], m["content"]) == "youtube"]) >= 2:
                break
    rag_messages = rag_messages[:3]

    sources = []  # attribution list returned to caller

    if rag_messages:
        yt_chunks = []
        chat_chunks = []
        for m in rag_messages[:3]:
            source_type = _classify_source(m["session_id"], m["content"])
            if source_type == "youtube":
                yt_chunks.append(m)
            else:
                chat_chunks.append(m)

            if source_type == "youtube":
                title = _extract_yt_title(m["content"])
                if title and not any(s.get("title") == title for s in sources):
                    sources.append({
                        "type": "youtube",
                        "title": title,
                        "url": _resolve_yt_url(m["session_id"]) or _youtube_search_url(title),
                        "session_id": m["session_id"],
                    })

        system_prompt_parts = ["You are a Second Brain AI assistant."]

        if yt_chunks:
            yt_content = "\n\n".join(
                f'[Knowledge from YouTube video: {(_extract_yt_title(m["content"]) or m["session_id"])}]\n{m["content"]}'
                for m in yt_chunks
            )
            system_prompt_parts.append(
                "You have access to transcripts from YouTube videos the user has previously watched or subscribed to. "
                "Treat these as authoritative knowledge the user has chosen to remember. "
                "If the user's question is answered by a transcript, draw on it confidently.\n\n"
                f"{yt_content}"
            )

        if chat_chunks:
            chat_content = "\n\n".join(
                f'[Memory: past conversation - {m["session_id"][:8]}...] {m["role"]}: {m["content"]}'
                for m in chat_chunks
            )
            system_prompt_parts.append(
                "The following are excerpts from the user's past conversations with you. "
                "Use them for personal context and continuity.\n\n"
                f"{chat_content}"
            )

        if not yt_chunks and not chat_chunks:
            system_prompt_parts.append("Answer the user's question directly.")

        messages.insert(0, {"role": "system", "content": "\n\n".join(system_prompt_parts)})

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
    msg_id = save_message(session_id=session_id, role="assistant", content=ai_content)
    store_embedding(message_id=msg_id, text=ai_content, session_id=session_id, role="assistant")

    # Proactive suggestion check (background, don't block)
    suggestion = None
    try:
        suggestions = get_proactive_suggestions(user_message, session_id, limit=2)
        if suggestions:
            narrative = _generate_suggestion_narrative(user_message, suggestions)
            if narrative:
                suggestion = {
                    "text": narrative,
                    "session_id": suggestions[0]["session_id"],
                    "preview": suggestions[0]["preview"],
                }
    except Exception as e:
        logger.debug("Proactive suggestion error: %s", e)

    return ai_content, suggestion, sources