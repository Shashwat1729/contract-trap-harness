"""Simple in-memory cache — efficiency win for eval."""
from functools import lru_cache
import time

@lru_cache(maxsize=1024)
def cached_process(query: str) -> str:
    # import here to avoid circular deps at kickoff
    from advanced.src.core import process
    return process(query)

# For TTL behavior, swap to cachetools.TTLCache at kickoff if needed
