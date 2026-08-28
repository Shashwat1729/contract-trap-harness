"""
Advanced entrypoint — Verification-gated Contract Trap Harness, production-grade.

Implements Harbor-like I/O + 5-dim rubric compatibility, with citation-gated commitments.
Human approval required before recommendation reaches reviewer as approved candidate (Rule 04/05).
"""
from __future__ import annotations

import time
import logging
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.config import PORT, LOG_LEVEL, MODEL, HARNESS_MODE, ENABLE_VERIFY, ENABLE_MEMORY
from src.core import process_contract_advanced
from src.harness.ingest import extract_text_with_pages, Page
from src.harness.memory import NegotiationMemory
from src.fallback.handler import fallback_response

logging.basicConfig(level=LOG_LEVEL.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("advanced")

app = FastAPI(
    title="Frontier Challenge — Advanced (Contract Trap Harness)",
    version="0.3.0",
    description="Verification-gated redlining: discover -> reason -> evidence -> verify -> human review as approved candidate.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADVANCED_FEATURES = ["verification-gated", "citation-provenance", "surgical-edits", "negotiation-memory", "tier-aware-harness", "fallback-sandbox"]

# In-memory negotiation memory per contract (production would persist to DB)
_memories: dict[str, NegotiationMemory] = {}


class RedlineRequest(BaseModel):
    contract_text: str = Field(..., min_length=1)
    contract_id: str = Field(default="contract_01")
    party: str = Field(default="AgentCo")
    turn: int = Field(default=1, ge=1, le=4)
    model: str = Field(default="gpt-4o-mini")
    harness_mode: str = Field(default="auto", description="auto|light|balanced|strict")


class RedlineResponse(BaseModel):
    variant: str
    contract_id: str
    turn: int
    harness_mode: str
    trap_count: int
    total_proposed: int
    evidence_supported: int
    unsupported: int
    surgical_rate: float
    findings: list[dict]
    trap_interactions: list[dict]
    latency_ms: int
    features: list[str]


@app.get("/health")
def health():
    return {"status": "ok", "variant": "advanced", "version": "0.3.0", "features": ADVANCED_FEATURES}


@app.get("/api/example")
def example(q: str = "hello"):
    return {"variant": "advanced", "query": q, "result": f"advanced processed (verified): {q}", "verified": True}


@app.post("/api/example")
def example_post(payload: dict):
    if not payload:
        return {"variant": "advanced", "error": "empty payload", "fallback": fallback_response("empty", "empty payload"), "verified": False}
    return {"variant": "advanced", "received": payload, "result": "ok", "verified": True}


@app.post("/api/redline", response_model=RedlineResponse)
def redline(req: RedlineRequest):
    t0 = time.perf_counter()
    # Ingest -> paginate for page:line
    # If contract_text is already text, paginate by 2500 chars
    full_text = req.contract_text
    if len(full_text) > 120000:
        full_text = full_text[:120000]
    # Build pages
    pages: list[Page] = []
    chars_per_page = 2500
    for i in range(0, len(full_text), chars_per_page):
        num = i // chars_per_page + 1
        chunk = full_text[i: i + chars_per_page]
        pages.append(Page(num=num, text=chunk, start=i, end=i + len(chunk)))
    if not pages:
        pages.append(Page(num=1, text=full_text, start=0, end=len(full_text)))

    # Memory: get or create
    mem = None
    if ENABLE_MEMORY:
        mem = _memories.get(req.contract_id)
        if mem is None:
            mem = NegotiationMemory(contract_id=req.contract_id, turn=req.turn)
            _memories[req.contract_id] = mem

    try:
        result = process_contract_advanced(
            contract_text=full_text,
            pages=pages,
            contract_id=req.contract_id,
            turn=req.turn,
            memory=mem,
            model=req.model,
            harness_mode=req.harness_mode if req.harness_mode != "auto" else HARNESS_MODE,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa
        log.exception("advanced redline failed")
        # Fallback sandbox: never expose stack, return graceful fallback per Rule 04
        fb = fallback_response(req.contract_id, f"{type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=fb)

    latency_ms = int((time.perf_counter() - t0) * 1000)
    return RedlineResponse(
        variant="advanced",
        contract_id=result["contract_id"],
        turn=result["turn"],
        harness_mode=result["harness_mode"],
        trap_count=result["trap_count"],
        total_proposed=result["total_proposed"],
        evidence_supported=result["evidence_supported"],
        unsupported=result["unsupported"],
        surgical_rate=result["surgical_rate"],
        findings=result["findings"],
        trap_interactions=result["trap_interactions"],
        latency_ms=latency_ms,
        features=ADVANCED_FEATURES,
    )


@app.post("/api/trap-detect")
def trap_detect(req: RedlineRequest):
    return redline(req)


@app.get("/api/memory/{contract_id}")
def get_memory(contract_id: str):
    mem = _memories.get(contract_id)
    if not mem:
        raise HTTPException(status_code=404, detail="no memory for contract_id")
    return {"contract_id": contract_id, "memory": mem.to_context(), "raw": mem.__dict__}


@app.post("/api/memory/{contract_id}/reset")
def reset_memory(contract_id: str):
    _memories.pop(contract_id, None)
    return {"status": "reset", "contract_id": contract_id}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=PORT, reload=True)
