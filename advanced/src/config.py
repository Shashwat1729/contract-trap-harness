"""Advanced config — production, tier-aware harness selector."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

PORT: int = int(os.getenv("PORT", "8001"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
MODEL: str = os.getenv("MODEL", os.getenv("ADVANCED_MODEL", "gpt-4o-mini"))
HARNESS_MODE: str = os.getenv("HARNESS_MODE", "auto")  # auto | light | balanced | strict
MAX_CHARS: int = int(os.getenv("MAX_CHARS", "120000"))
ENABLE_VERIFY: bool = os.getenv("ENABLE_VERIFY", "1") == "1"
ENABLE_MEMORY: bool = os.getenv("ENABLE_MEMORY", "1") == "1"
ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "1") == "1"
