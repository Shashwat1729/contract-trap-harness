"""
Verification layer — self-correction / output validation.
Wire real checks at kickoff (schema validation, ground-truth comparison, LLM-as-judge).
"""

def verify(output: str, query: str = "") -> dict:
    """Return {ok: bool, output: str, reason: str}"""
    if not output:
        return {"ok": False, "output": output, "reason": "empty output"}
    # Stub: add real verification (e.g., regex, schema, secondary model)
    return {"ok": True, "output": output, "reason": "passed"}

def retry_with_verify(fn, query: str, max_retries: int = 2):
    last = None
    for i in range(max_retries + 1):
        out = fn(query)
        v = verify(out, query)
        if v["ok"]:
            return out
        last = v
    return out  # return last attempt even if unverified
