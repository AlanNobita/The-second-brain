"""
One-time backfill: re-create yt_* session messages from existing obsidian-ingest markdown notes
and re-embed them in ChromaDB.

Use this when the messages table has been wiped but obsidian-ingest/*.md notes still exist.
Idempotent: skips notes whose session_id already has messages.

Usage:
    python scripts/backfill_yt_messages.py
"""
import os
import glob
import logging
from uuid import uuid4

from app import create_app
from app.models.db import save_message, get_connection
from app.models.youtube_db import _get_conn as yt_get_conn, get_ingested_videos
from app.services.embedding_service import store_embedding, init_embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBSIDIAN_PATH = os.path.join(PROJECT_ROOT, "obsidian-ingest")
CHUNK_MAX_CHARS = 1800


def _slug_to_title(slug: str) -> str:
    return slug.replace("-", " ")


def _match_session_id(filename: str, ingested_videos: list) -> str | None:
    """Match a markdown filename back to its ingested_videos session_id by video_id or title."""
    base = os.path.basename(filename).rsplit(".", 1)[0]

    for row in ingested_videos:
        if row["video_id"] in base:
            return row["session_id"]

    if base.startswith("20"):
        title_slug = base[11:]
    else:
        title_slug = base
    title_norm = _slug_to_title(title_slug).lower()

    for row in ingested_videos:
        if _slug_to_title(row["video_title"]).lower() == title_norm:
            return row["session_id"]

    return None


def backfill_yt_messages():
    app = create_app()
    with app.app_context():
        init_embedding_service()

        md_files = glob.glob(os.path.join(OBSIDIAN_PATH, "*.md"))
        logger.info("Found %d markdown notes in %s", len(md_files), OBSIDIAN_PATH)

        ingested = get_ingested_videos(limit=1000)
        video_id_to_session = {row["video_id"]: row["session_id"] for row in ingested}
        logger.info("Loaded %d ingested_videos rows", len(video_id_to_session))

        backfilled = 0
        skipped = 0
        unmatched = 0

        for md_path in md_files:
            session_id = _match_session_id(md_path, ingested)

            if session_id is None:
                session_id = f"yt_{uuid4().hex[:12]}"
                unmatched += 1
                logger.warning("No match for %s — using fresh session_id %s", os.path.basename(md_path), session_id)

            with get_connection() as conn:
                existing = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
                ).fetchone()[0]
            if existing > 0:
                logger.info("Skip %s — already has %d messages", session_id, existing)
                skipped += 1
                continue

            with open(md_path, "r", encoding="utf-8") as f:
                markdown = f.read()

            chunks = []
            current_chunk = ""
            for line in markdown.split("\n"):
                if len(current_chunk) + len(line) > CHUNK_MAX_CHARS:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"
            if current_chunk:
                chunks.append(current_chunk)

            base = os.path.basename(md_path).rsplit(".", 1)[0]
            if base.startswith("20"):
                title = _slug_to_title(base[11:])
            else:
                title = _slug_to_title(base)

            for i, chunk in enumerate(chunks):
                prefix = f"[YouTube] {title} ({i+1}/{len(chunks)})"
                content = f"{prefix}\n\n{chunk}"
                msg_id = save_message(session_id, "assistant", content)
                store_embedding(msg_id, content, session_id, "assistant")

            logger.info("Backfilled %s (%s) — %d chunks", session_id, title, len(chunks))
            backfilled += 1

        logger.info("Done. backfilled=%d skipped=%d unmatched=%d", backfilled, skipped, unmatched)


if __name__ == "__main__":
    backfill_yt_messages()
