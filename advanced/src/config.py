"""Advanced config — mirrors baseline + advanced flags."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

PORT = int(os.getenv("PORT", "8001"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "1") == "1"
ENABLE_VERIFY = os.getenv("ENABLE_VERIFY", "1") == "1"
