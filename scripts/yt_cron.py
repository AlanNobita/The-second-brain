#!/usr/bin/env python3
"""Standalone YouTube ingestion for GitHub Actions cron."""
import json, os, sys, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("yt_cron")

REPO = Path(__file__).resolve().parent.parent
os.chdir(str(REPO))
sys.path.insert(0, str(REPO))
os.environ.setdefault("OBSIDIAN_NOTES_PATH", str(REPO / "data" / "notes"))
os.environ["SKIP_EMBEDDINGS"] = "true"

DB_PATH = REPO / "second_brain.db"
SEED_PATH = REPO / "data" / "subscriptions.json"

# Seed DB if it doesn't exist (first run or artifact expired)
if not DB_PATH.exists() and SEED_PATH.exists():
    logger.info("No DB found — seeding from %s", SEED_PATH)
    from app.models.youtube_db import init_youtube_db
    from app.models.db import init_db
    from app.models.kg_db import init_kg_db
    init_db()
    init_youtube_db()
    init_kg_db()
    subs = json.loads(SEED_PATH.read_text())
    if subs:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.executemany(
            "INSERT OR IGNORE INTO subscriptions (channel_url, channel_name) VALUES (?, ?)",
            [(s["channel_url"], s["channel_name"]) for s in subs]
        )
        conn.commit()
        conn.close()
        logger.info("Imported %d subscriptions", len(subs))
elif DB_PATH.exists():
    logger.info("DB found at %s", DB_PATH)

logger.info("Starting Flask app…")
from app import create_app
app = create_app()

with app.app_context():
    from app.services.subscription_service import check_due_subscriptions
    check_due_subscriptions()
    logger.info("Ingestion complete")
