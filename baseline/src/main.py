"""
Baseline entrypoint — FastAPI, production-grade.

Implements Harbor-like I/O: contract text in, redlines + findings out via tracked changes style.
No verification gating, no memory — single-pass.
"""
from __future__ import annotations

import os
import time
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.core import process_contract, health_check
from src.config import PORT, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("baseline")

app = FastAPI(
    title="Frontier Challenge — Baseline (Contract Trap Single-Pass)",
    version="0.2.0",
    description="Baseline: single-pass clause trap detector. No verification gating, no memory.",
)

app.add_middleware(
    CORSMiddleware,
    # Wildcard origins + credentials is rejected by browsers; this API uses no cookies.
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()] or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RedlineRequest(BaseModel):
    contract_text: str = Field(..., min_length=1, description="Full contract text or extracted DOCX text")
    contract_id: str = Field(default="contract_01")
    party: str = Field(default="AgentCo")
    turn: int = Field(default=1, ge=1, le=4)


class EvidenceOut(BaseModel):
    clause_type: str
    span_text: str
    page: int
    line: int
    start: int
    end: int
    confidence: float
    rule_id: str
    precedent: str


class FindingOut(BaseModel):
    trap_id: str
    clause_type: str
    risk: str
    span_text: str
    page: int
    line: int
    evidence: EvidenceOut
    proposed_change: str
    rationale: str


class RedlineResponse(BaseModel):
    variant: str
    contract_id: str
    turn: int
    trap_count: int
    findings: list[FindingOut]
    evidence_supported: int
    unsupported: int
    latency_ms: int


@app.get("/health")
def health():
    return {**health_check(), "version": "0.2.0"}


@app.get("/api/example")
def example(q: str = "hello"):
    return {"variant": "baseline", "query": q, "result": f"baseline processed: {q}"}


@app.post("/api/example")
def example_post(payload: dict):
    return {"variant": "baseline", "received": payload, "result": "ok"}


@app.post("/api/redline", response_model=RedlineResponse)
def redline(req: RedlineRequest):
    t0 = time.perf_counter()
    try:
        result = process_contract(req.contract_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # noqa
        log.exception("redline failed")
        raise HTTPException(status_code=500, detail=f"redline failed: {type(e).__name__}") from e
    latency_ms = int((time.perf_counter() - t0) * 1000)
    # Build typed findings
    findings = []
    for f in result["findings"]:
        ev = f["evidence"]
        findings.append(FindingOut(
            trap_id=f["trap_id"],
            clause_type=f["clause_type"],
            risk=f["risk"],
            span_text=f["span_text"],
            page=f["page"],
            line=f["line"],
            evidence=EvidenceOut(**ev),
            proposed_change=f["proposed_change"],
            rationale=f["rationale"],
        ))
    return RedlineResponse(
        variant="baseline",
        contract_id=req.contract_id,
        turn=req.turn,
        trap_count=result["trap_count"],
        findings=findings,
        evidence_supported=result["evidence_supported"],
        unsupported=result["unsupported"],
        latency_ms=latency_ms,
    )


@app.post("/api/trap-detect")
def trap_detect(req: RedlineRequest):
    """Alias for /api/redline for harness eval compatibility."""
    return redline(req)


if __name__ == "__main__":
    uvicorn.run("src.main:app", host=os.getenv("HOST", "0.0.0.0"), port=PORT, reload=os.getenv("UVICORN_RELOAD", "0") == "1")
