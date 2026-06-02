from flask import Blueprint, jsonify, request, current_app
from uuid import uuid4
from ..services.youtube_service import search_youtube, fetch_transcript, extract_video_id
from ..services.note_service import debloat_and_structure, save_note_file
from ..services.subscription_service import subscribe, unsubscribe, list_subscriptions
from ..models.youtube_db import add_ingested_video
from ..models.db import save_message
from ..services.embedding_service import store_embedding

youtube_bp = Blueprint("youtube", __name__)


@youtube_bp.route("/yt/search", methods=["GET"])
def yt_search():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    results = search_youtube(query, max_results=5)
    return jsonify(results)


@youtube_bp.route("/yt/ingest", methods=["POST"])
def yt_ingest():
    data = request.get_json(silent=True) or {}
    video_url = data.get("video_url", "")
    if not video_url:
        return jsonify({"error": "video_url is required"}), 400
    session_id = f"yt_{uuid4().hex[:12]}"
    try:
        transcript = fetch_transcript(video_url)
        vid = extract_video_id(video_url)
        title = f"Ingested Video ({vid})" if vid else "Unknown Video"
        markdown = debloat_and_structure(transcript, title, "YouTube")
        if markdown is None:
            current_app.logger.exception(
                "debloat_and_structure returned None in yt_ingest(video_url=%r)",
                video_url,
            )
            return jsonify({"error": "failed to structure transcript"}), 500
        lines = markdown.split("\n")
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) > 1800:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
        if current_chunk:
            chunks.append(current_chunk)
        for i, chunk in enumerate(chunks):
            prefix = f"[YouTube Ingestion] ({i+1}/{len(chunks)})"
            msg_id = save_message(session_id, "assistant", f"{prefix}\n\n{chunk}")
            store_embedding(msg_id, f"{prefix}\n\n{chunk}", session_id, "assistant")
        from datetime import datetime, timezone
        ingested_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = save_note_file(markdown, title, ingested_date)
        add_ingested_video(
            video_id=vid or "unknown",
            channel_name="YouTube",
            video_title=title,
            video_url=video_url,
            session_id=session_id,
            file_path=file_path,
        )
        return jsonify({"session_id": session_id, "file_path": file_path, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@youtube_bp.route("/yt/subscribe", methods=["POST"])
def yt_subscribe():
    data = request.get_json(silent=True) or {}
    channel_url = data.get("channel_url", "")
    if not channel_url:
        return jsonify({"error": "channel_url is required"}), 400
    sub = subscribe(channel_url)
    return jsonify(sub)


@youtube_bp.route("/yt/unsubscribe", methods=["POST"])
def yt_unsubscribe():
    data = request.get_json(silent=True) or {}
    sub_id = data.get("sub_id")
    if not sub_id:
        return jsonify({"error": "sub_id is required"}), 400
    # sub_id must be an integer (or a string that's parseable as one) so
    # downstream SQL doesn't blow up on a list or dict.
    if isinstance(sub_id, bool) or not isinstance(sub_id, (int, str)):
        return jsonify({"error": "sub_id must be an integer"}), 400
    try:
        sub_id_int = int(sub_id)
    except (TypeError, ValueError):
        return jsonify({"error": "sub_id must be an integer"}), 400
    result = unsubscribe(sub_id_int)
    return jsonify({"status": "ok" if result else "not_found"})


@youtube_bp.route("/yt/subscriptions", methods=["GET"])
def yt_subscriptions():
    subs = list_subscriptions()
    return jsonify(subs)


@youtube_bp.route("/yt/channel", methods=["POST"])
def yt_channel():
    data = request.get_json(silent=True) or {}
    channel_url = data.get("channel_url", "")
    if not channel_url:
        return jsonify({"error": "channel_url is required"}), 400
    from ..services.youtube_service import get_channel_videos
    videos = get_channel_videos(channel_url, max_results=5)
    ingested = []
    for video in videos:
        from ..services.subscription_service import _ingest_single_video
        try:
            _ingest_single_video(video, video.get("channel", "Unknown"))
            ingested.append({"title": video["title"], "video_id": video["video_id"]})
        except Exception:
            continue
    return jsonify({"ingested_count": len(ingested), "videos": ingested})
