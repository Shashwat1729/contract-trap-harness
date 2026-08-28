"""
Baseline entrypoint — FastAPI app.
Replace routes/core at kickoff. This scaffold just proves `make run-baseline` and health checks work.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(
    title="Frontier Challenge — Baseline",
    version="0.1.0",
    description="Baseline: simple, correct, minimal. Replace with real problem at kickoff.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "variant": "baseline", "version": "0.1.0"}

@app.get("/api/example")
def example(q: str = "hello"):
    """Placeholder — replace with real problem endpoint at kickoff. Keep signature typed."""
    return {"variant": "baseline", "query": q, "result": f"baseline processed: {q}"}

@app.post("/api/example")
def example_post(payload: dict):
    return {"variant": "baseline", "received": payload, "result": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)
