"""Baseline config — env only, no secrets committed."""
import os
from pathlib import Path

# Load .env if present (python-dotenv optional)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
# Add problem-specific keys at kickoff, e.g.:
# API_KEY = os.getenv("API_KEY", "")
