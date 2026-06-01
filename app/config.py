import os 
from dotenv import load_dotenv

load_dotenv() # reads .env file and loads environment variables into the environment

class Config: 
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL",
        "https://opencode.ai/zen/v1"
    )
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek-v4-flash-free")

    YT_CHECK_INTERVAL_HOURS = int(os.getenv("YT_CHECK_INTERVAL_HOURS", "6"))
    YT_MAX_PER_CHECK = int(os.getenv("YT_MAX_PER_CHECK", "5"))
    OBSIDIAN_NOTES_PATH = os.getenv("OBSIDIAN_NOTES_PATH", os.path.join(os.path.dirname(__file__), "..", "obsidian-ingest"))
