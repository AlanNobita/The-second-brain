"""
Re-embed YouTube messages in SQLite that don't have ChromaDB embeddings.

After clearing orphan vectors, run this to restore the vector index.
"""
import logging
from app import create_app
from app.models.db import get_connection
from app.services import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reembed_yt_messages():
    app = create_app()
    with app.app_context():
        embedding_service.init_embedding_service()
        coll = embedding_service._collection
        if coll is None:
            logger.error("ChromaDB not initialized")
            return

        total_in_chroma = coll.count()
        chroma_ids = {id_ for id_ in coll.get(limit=total_in_chroma)["ids"]}

        with get_connection() as conn:
            yt_rows = conn.execute(
                "SELECT id, session_id, role, content FROM messages WHERE session_id LIKE 'yt_%'"
            ).fetchall()

        to_embed = [r for r in yt_rows if str(r["id"]) not in chroma_ids]
        logger.info("Found %d yt messages, %d already embedded, %d need re-embedding",
                    len(yt_rows), len(yt_rows) - len(to_embed), len(to_embed))

        for row in to_embed:
            embedding_service.store_embedding(
                message_id=row["id"],
                text=row["content"],
                session_id=row["session_id"],
                role=row["role"],
            )

        logger.info("Done. ChromaDB now has %d vectors", coll.count())


if __name__ == "__main__":
    reembed_yt_messages()
