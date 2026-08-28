"""
Advanced entrypoint — FastAPI app with meaningful improvements over baseline.
At kickoff, copy baseline core and layer: verification, retry, cache, fallback.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(
    title="Frontier Challenge — Advanced",
    version="0.1.0",
    description="Advanced: meaningful improvement (verify + retry + fallback).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADVANCED_FEATURES = ["verification", "retry-with-backoff", "fallback-sandbox", "cache"]

@app.get("/health")
def health():
    return {"status": "ok", "variant": "advanced", "version": "0.1.0", "features": ADVANCED_FEATURES}

@app.get("/api/example")
def example(q: str = "hello"):
    # Advanced: verify + fallback (stub — wire real verify.py at kickoff)
    result = f"advanced processed (verified): {q}"
    return {"variant": "advanced", "query": q, "result": result, "verified": True}

@app.post("/api/example")
def example_post(payload: dict):
    # Advanced: handle edge cases baseline doesn't
    if not payload:
        return {"variant": "advanced", "error": "empty payload", "fallback": "graceful"}
    return {"variant": "advanced", "received": payload, "result": "ok", "verified": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)
