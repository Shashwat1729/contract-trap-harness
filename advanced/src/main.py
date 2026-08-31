"""
Advanced entrypoint — Verification-gated Contract Trap Harness, production-grade.

Implements Harbor-like I/O + 5-dim rubric compatibility, with citation-gated commitments.
Human approval required before recommendation reaches reviewer as approved candidate (Rule 04/05).
"""
from __future__ import annotations

import time
import logging
from typing import Optional, Literal, Any, AsyncIterator

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from src.config import PORT, LOG_LEVEL, MODEL, HARNESS_MODE, ENABLE_VERIFY, ENABLE_MEMORY, ENABLE_LANGGRAPH
from src.core import process_contract_advanced, process_contract_graph
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

ADVANCED_FEATURES = ["verification-gated", "citation-provenance", "surgical-edits", "negotiation-memory", "tier-aware-harness", "fallback-sandbox", "agentic-langgraph-mode"]

# In-memory negotiation memory per contract (production would persist to DB)
_memories: dict[str, NegotiationMemory] = {}


class RedlineRequest(BaseModel):
    contract_text: str = Field(..., min_length=1)
    contract_id: str = Field(default="contract_01")
    party: str = Field(default="AgentCo")
    turn: int = Field(default=1, ge=1, le=4)
    model: str = Field(default="gpt-4o-mini")
    harness_mode: str = Field(default="auto", description="auto|light|balanced|strict")
    engine: str = Field(default="auto", description="auto (respects ENABLE_LANGGRAPH env) | direct (single-function pipeline) | graph (LangGraph agentic StateGraph: extract->risk->evidence->verify->[revise->verify]->human_review, always falls back to direct on any graph-invoke exception)")


class RedlineResponse(BaseModel):
    variant: str
    contract_id: str
    turn: int
    harness_mode: str
    engine: str = Field(default="direct", description="Which pipeline actually ran this request: direct | langgraph | direct-fallback (graph was requested but its invoke raised, so it fell back).")
    status: str = Field(default="complete", description="complete | pending_human_review (real langgraph interrupt() fired — engine=langgraph + ENABLE_GRAPH_INTERRUPT=1 + at least one REJECTed finding). When pending, findings/trap_count etc. are empty placeholders — call POST /api/harness/resume with `interrupt` and `thread_id` to continue.")
    thread_id: Optional[str] = Field(default=None, description="LangGraph checkpoint thread id — required to resume a pending_human_review response via /api/harness/resume.")
    interrupt: Optional[dict[str, Any]] = Field(default=None, description="Present only when status=pending_human_review: {kind, contract_id, pending_rejected: [{override_key, clause_type, risk, reasons, proposed_change}], approved_count}.")
    trap_count: int
    total_proposed: int
    evidence_supported: int
    unsupported: int
    surgical_rate: float
    findings: list[dict[str, Any]]
    trap_interactions: list[dict[str, Any]]
    coverage_gaps: list[dict[str, Any]] = Field(default_factory=list, description="Playbook rules with no clause found at all (e.g. missing Termination for Convenience) -- distinct from findings, which require a matched clause.")
    dual_stats: dict[str, Any] = Field(default_factory=dict, description="Deterministic dual-threshold gate agreement counts: agree_pass / agree_reject / disagree.")
    llm_stats: dict[str, Any] = Field(default_factory=dict, description="Real LLM cross-check counters: ran / confirmed / flagged / skipped / mock.")
    latency_ms: int
    features: list[str]


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "variant": "advanced", "version": "0.3.0", "features": ADVANCED_FEATURES, "langgraph_default_on": ENABLE_LANGGRAPH}


@app.get("/api/example")
def example(q: str = "hello") -> dict[str, Any]:
    return {"variant": "advanced", "query": q, "result": f"advanced processed (verified): {q}", "verified": True}


@app.post("/api/example")
def example_post(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {"variant": "advanced", "error": "empty payload", "fallback": fallback_response("empty", "empty payload"), "verified": False}
    return {"variant": "advanced", "received": payload, "result": "ok", "verified": True}


@app.post("/api/redline", response_model=RedlineResponse)
async def redline(req: RedlineRequest) -> RedlineResponse:
    # Timeout handling: 30s for harness, non-blocking via run_in_executor for CPU-bound extract
    try:
        return await asyncio.wait_for(_redline_sync(req), timeout=30.0)
    except asyncio.TimeoutError:
        log.warning("redline timeout for %s", req.contract_id)
        raise HTTPException(status_code=504, detail=fallback_response(req.contract_id, "timeout 30s"))

async def _redline_sync(req: RedlineRequest) -> RedlineResponse:
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
        result = process_contract_graph(
            contract_text=full_text,
            pages=pages,
            contract_id=req.contract_id,
            turn=req.turn,
            memory=mem,
            model=req.model,
            harness_mode=req.harness_mode if req.harness_mode != "auto" else HARNESS_MODE,
            engine=req.engine,
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
        engine=result.get("engine", "direct"),
        status=result.get("status", "complete"),
        thread_id=result.get("thread_id"),
        interrupt=result.get("interrupt"),
        trap_count=result["trap_count"],
        total_proposed=result["total_proposed"],
        evidence_supported=result["evidence_supported"],
        unsupported=result["unsupported"],
        surgical_rate=result["surgical_rate"],
        findings=result["findings"],
        trap_interactions=result["trap_interactions"],
        coverage_gaps=result.get("coverage_gaps", []),
        dual_stats=result.get("dual_stats", {}),
        llm_stats=result.get("llm_stats", {}),
        latency_ms=latency_ms,
        features=ADVANCED_FEATURES,
    )


@app.post("/api/trap-detect")
async def trap_detect(req: RedlineRequest) -> RedlineResponse:
    return await redline(req)


class ResumeRequest(BaseModel):
    contract_id: str = Field(..., description="The contract_id from the original pending_human_review response.")
    thread_id: str = Field(..., description="The thread_id from the original pending_human_review response.")
    approve_keys: list[str] = Field(default_factory=list, description="override_key values (from the interrupt payload's pending_rejected list) that a human reviewer wants to approve despite the deterministic gate's REJECT. Anything not listed here stays REJECTed.")


@app.post("/api/harness/resume", response_model=RedlineResponse)
async def harness_resume(req: ResumeRequest) -> RedlineResponse:
    """Resumes a graph run that paused at a real langgraph interrupt() inside human_review_node
    (ENABLE_GRAPH_INTERRUPT=1). A human reviewer decides which REJECTed findings to override
    to approved; the graph then finishes with those overrides applied and audit-marked
    (verification="PASS (human override)", human_override=True) -- never a silent approval."""
    t0 = time.perf_counter()
    try:
        result = process_contract_graph(
            contract_id=req.contract_id, thread_id=req.thread_id,
            resume_decision={"approve_keys": req.approve_keys},
        )
    except Exception as e:  # noqa
        log.exception("harness resume failed")
        raise HTTPException(status_code=422, detail=f"resume failed (was thread_id={req.thread_id} actually interrupted? {type(e).__name__}: {e}")
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return RedlineResponse(
        variant="advanced", contract_id=result["contract_id"], turn=result["turn"],
        harness_mode=result["harness_mode"], engine=result.get("engine", "langgraph"),
        status=result.get("status", "complete"), thread_id=result.get("thread_id"), interrupt=result.get("interrupt"),
        trap_count=result["trap_count"], total_proposed=result["total_proposed"],
        evidence_supported=result["evidence_supported"], unsupported=result["unsupported"],
        surgical_rate=result["surgical_rate"], findings=result["findings"],
        trap_interactions=result["trap_interactions"], coverage_gaps=result.get("coverage_gaps", []),
        dual_stats=result.get("dual_stats", {}), llm_stats=result.get("llm_stats", {}),
        latency_ms=latency_ms, features=ADVANCED_FEATURES,
    )

@app.get("/api/harness/stream")
async def harness_stream(contract_id: str = "demo") -> StreamingResponse:
    """
    Real SSE progress: runs process_contract_advanced on shared/fixtures/contracts/{contract_id}.txt
    in a worker thread and streams each stage as it genuinely completes (via the on_stage
    callback), not a canned/fake sequence. Falls back to a clear error event if the fixture
    is missing rather than pretending to have run.
    """
    import queue
    import threading
    from pathlib import Path as _Path

    fixture = _Path(__file__).parents[2] / "shared" / "fixtures" / "contracts" / f"{contract_id}.txt"
    if not fixture.exists():
        async def err_gen() -> AsyncIterator[str]:
            yield f"data: error: fixture not found for contract_id={contract_id}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    text = fixture.read_text(encoding="utf-8", errors="ignore")
    text = text[:120000]
    pages: list[Page] = []
    for i in range(0, len(text), 2500):
        chunk = text[i : i + 2500]
        pages.append(Page(num=i // 2500 + 1, text=chunk, start=i, end=i + len(chunk)))
    if not pages:
        pages.append(Page(num=1, text=text, start=0, end=len(text)))

    q: "queue.Queue[str]" = queue.Queue()
    STAGE_LABELS = {
        "extract": "Extractor: scanning CUAD types -> SaaS playbook clauses",
        "risk": "Risk: playbook + precedent retrieval",
        "verify": "Verifier: gating on page:line provenance",
        "route": "Router: routed to human review as candidate",
    }

    def _on_stage(stage: str, detail: str) -> None:
        label = STAGE_LABELS.get(stage, stage)
        q.put(f"{label} -- {detail}")

    def _run() -> None:
        try:
            process_contract_advanced(text, pages, contract_id=contract_id, turn=1, on_stage=_on_stage)
        except Exception as e:  # noqa
            q.put(f"__error__ {type(e).__name__}: {e}")
        finally:
            q.put("__done__")

    async def gen() -> AsyncIterator[str]:
        threading.Thread(target=_run, daemon=True).start()
        loop = asyncio.get_event_loop()
        while True:
            item = await loop.run_in_executor(None, q.get)
            if item == "__done__":
                yield "data: done\n\n"
                break
            if item.startswith("__error__"):
                yield f"data: error: {item[len('__error__ '):]}\n\n"
                break
            yield f"data: {item}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/memory/{contract_id}")
def get_memory(contract_id: str) -> dict[str, Any]:
    mem = _memories.get(contract_id)
    if not mem:
        raise HTTPException(status_code=404, detail="no memory for contract_id")
    return {"contract_id": contract_id, "memory": mem.to_context(), "raw": mem.__dict__}


@app.post("/api/memory/{contract_id}/reset")
def reset_memory(contract_id: str) -> dict[str, Any]:
    _memories.pop(contract_id, None)
    return {"status": "reset", "contract_id": contract_id}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=PORT, reload=True)
