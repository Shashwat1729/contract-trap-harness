"""
Fallback / sandbox handler — for hidden dependencies, rate limits, offline judging.
Rule Book: "Keep consequential actions controlled through a sandbox or simulation."
"""
def fallback(query: str, reason: str = "unknown") -> dict:
    return {
        "variant": "advanced",
        "result": f"fallback for '{query}' — reason: {reason}",
        "fallback": True,
        "verified": False,
    }
