"""
Shared persistence for the per-module "thinking logs" (RiskWise Developer View).

Every harness module keeps its own bounded in-memory THINKING_LOG. Historically each
module also rewrote an evidence/reviews/thinking_<module>.json file on EVERY log call:
dozens of full JSON rewrites per contract in the request hot path (~75% of the advanced
pipeline's wall-clock time on the 30-fixture suite), with no locking, so concurrent API
requests could interleave writes and leave a truncated/corrupt file.

Now:
  - per-entry module files are opt-in (THINKING_LOG_PERSIST=1) and written atomically;
  - core.py's one-per-contract snapshot (evidence/reviews/thinking_<id>_t<turn>.json,
    which already aggregates core/risk/verify thinking) stays on by default and is also
    written atomically, under a sanitized filename (contract_id is caller-controlled).
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("advanced.harness.thinking")

REVIEWS_DIR = Path(__file__).parents[2] / "evidence" / "reviews"
_lock = threading.Lock()


def persist_every_entry() -> bool:
    return os.getenv("THINKING_LOG_PERSIST", "0") == "1"


def snapshots_enabled() -> bool:
    return os.getenv("THINKING_SNAPSHOT", "1") == "1"


def safe_filename_part(value: str, max_len: int = 100) -> str:
    """Filesystem-safe token: no path separators, no leading dots, bounded length."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+|\.{2,}", "_", str(value)).lstrip(".")
    return cleaned[:max_len] or "unnamed"


def write_json_atomic(path: Path, data: Any) -> bool:
    """Write JSON via a temp file + os.replace so readers never see a partial file.
    Never raises; returns False on failure."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return True
    except Exception as e:
        logger.warning("thinking log write failed for %s: %s", path, e)
        return False


def persist_module_log(filename: str, entries: list[dict[str, Any]]) -> None:
    """Rewrite evidence/reviews/<filename> with `entries` -- only when THINKING_LOG_PERSIST=1."""
    if not persist_every_entry():
        return
    with _lock:
        write_json_atomic(REVIEWS_DIR / filename, list(entries))
