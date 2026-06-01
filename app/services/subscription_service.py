from ..models.youtube_db import (
    add_subscription as db_add_sub,
    remove_subscription as db_remove_sub,
    get_subscriptions as db_get_subs,
    get_subscription as db_get_sub,
    update_last_checked, mark_subscription_inactive,
    add_ingested_video, is_video_ingested,
)
from .youtube_service import get_channel_videos, fetch_transcript
from .note_service import debloat_and_structure, save_note_file
from ..models.db import save_message
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


def subscribe(channel_url):
    from .youtube_service import extract_channel_id
    cid = extract_channel_id(channel_url)
    channel_name = cid.lstrip("@").replace("-", " ").title()
    sub = db_add_sub(channel_url, channel_name)
    check_subscription(sub["id"])
    return sub


def unsubscribe(sub_id):
    return db_remove_sub(sub_id)


def list_subscriptions():
    return db_get_subs(only_active=True)


def check_subscription(sub_id):
    sub = db_get_sub(sub_id)
    if not sub or not sub["active"]:
        return 0
    try:
        videos = get_channel_videos(sub["channel_url"], max_results=5)
    except Exception as e:
        logger.warning("check_subscription(%s) — get_channel_videos failed: %s", sub_id, e)
        return 0
    new_count = 0
    for video in videos:
        if is_video_ingested(video["video_id"]):
            continue
        _ingest_single_video(video, sub["channel_name"])
        new_count += 1
    update_last_checked(sub_id)
    return new_count


def check_all_subscriptions():
    subs = db_get_subs(only_active=True)
    checked = 0
    total_new = 0
    for sub in subs:
        try:
            n = check_subscription(sub["id"])
            checked += 1
            total_new += n
        except Exception:
            continue
    return {"checked": checked, "new_videos": total_new}


def has_due_subscriptions():
    subs = db_get_subs(only_active=True)
    if not subs:
        return False
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    for sub in subs:
        if sub["last_checked"] is None or sub["last_checked"] < one_hour_ago:
            return True
    return False


def check_due_subscriptions():
    subs = db_get_subs(only_active=True)
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    for sub in subs:
        if sub["last_checked"] is not None and sub["last_checked"] >= one_hour_ago:
            continue
        try:
            check_subscription(sub["id"])
        except Exception as e:
            logger.warning("check_due_subscriptions — sub %s failed: %s", sub["id"], e)


def _ingest_single_video(video, channel_name):
    from .embedding_service import store_embedding
    session_id = f"yt_{uuid4().hex[:12]}"
    try:
        transcript = fetch_transcript(video["url"])
        markdown = debloat_and_structure(transcript, video["title"], channel_name)
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
            prefix = f"[YouTube] {video['title']} ({i+1}/{len(chunks)})"
            msg_id = save_message(session_id, "assistant", f"{prefix}\n\n{chunk}")
            store_embedding(msg_id, f"{prefix}\n\n{chunk}", session_id, "assistant")
        ingested_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = save_note_file(markdown, video["title"], ingested_date)
        add_ingested_video(
            video_id=video["video_id"],
            channel_name=channel_name,
            video_title=video["title"],
            video_url=video["url"],
            session_id=session_id,
            file_path=file_path,
        )
    except Exception as e:
        logger.warning("_ingest_single_video failed for %s: %s", video.get("video_id", "?"), e)
