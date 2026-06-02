"""
Clean orphan ChromaDB vectors — those whose message_id no longer exists in SQLite.

Use this after backfilling messages, when old embeddings still reference
non-existent rows.
"""
import logging

from app import create_app
from app.models.db import get_connection
from app.services import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_orphan_embeddings():
    app = create_app()
    with app.app_context():
        embedding_service.init_embedding_service()
        collection = embedding_service._collection
        if collection is None:
            logger.error("ChromaDB collection not initialized")
            return

        total = collection.count()
        all_data = collection.get(limit=total, include=["metadatas"])
        chroma_ids = all_data["ids"]

        with get_connection() as conn:
            rows = conn.execute("SELECT id FROM messages").fetchall()
        db_ids = {str(r["id"]) for r in rows}

        orphans = [id_ for id_ in chroma_ids if str(id_) not in db_ids]
        logger.info("ChromaDB vectors: %d, DB rows: %d, orphans: %d", total, len(db_ids), len(orphans))

        if orphans:
            collection.delete(ids=orphans)
            logger.info("Deleted %d orphan vectors", len(orphans))

        logger.info("Remaining: %d", collection.count())


if __name__ == "__main__":
    clear_orphan_embeddings()
