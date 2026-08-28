"""
Baseline core — pure domain logic.
Keep this framework-free so unit tests don't need FastAPI.
Replace with real problem logic at kickoff.
"""

def process(query: str) -> str:
    """Example pure function — replace at kickoff."""
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    return f"baseline processed: {query.strip()}"

def health_check() -> dict:
    return {"status": "ok", "variant": "baseline"}
