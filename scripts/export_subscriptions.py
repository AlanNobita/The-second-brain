#!/usr/bin/env python3
"""Export subscriptions from local second_brain.db to data/subscriptions.json.
Run this once to seed the GitHub Actions cron with your subscriptions."""
import json, sqlite3, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "second_brain.db"

if not DB.exists():
    print(f"ERROR: DB not found at {DB}")
    sys.exit(1)

conn = sqlite3.connect(str(DB))
rows = conn.execute(
    "SELECT channel_url, channel_name FROM subscriptions WHERE active = 1"
).fetchall()
conn.close()

subs = [{"channel_url": r[0], "channel_name": r[1]} for r in rows]
out = REPO / "data" / "subscriptions.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(subs, indent=2) + "\n")
print(f"Exported {len(subs)} subscriptions to {out}")
