from fastapi.testclient import TestClient
from src.main import app, ADVANCED_FEATURES

client = TestClient(app)

def test_health_has_features():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["variant"] == "advanced"
    assert "features" in j
    assert len(j["features"]) >= 1

def test_example_verified():
    r = client.get("/api/example", params={"q": "hello"})
    assert r.status_code == 200
    assert r.json()["verified"] is True

def test_empty_payload_fallback():
    r = client.post("/api/example", json={})
    assert r.status_code == 200
    assert r.json().get("fallback")

def test_redline_direct_engine():
    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods. Notice Period To Terminate Renewal: 30 days."
    r = client.post("/api/redline", json={"contract_text": contract, "contract_id": "api_direct", "engine": "direct"})
    assert r.status_code == 200
    j = r.json()
    assert j["engine"] == "direct"
    assert "trap_count" in j and "findings" in j

def test_redline_graph_engine_real_interrupt_and_resume(monkeypatch):
    """CHANGELOG #21: end-to-end proof the real human-in-the-loop interrupt/resume cycle is
    reachable through the actual HTTP API a client (or the dashboard) would use -- not just
    the langgraph mechanics in isolation (see test_graph.py for that). Forces a REJECT via
    a monkeypatched dual_verify_finding (real contract text alone rarely produces one --
    the playbook's canned proposed_change strings are short) so the test controls the
    scenario deterministically while still exercising the real FastAPI request/response path."""
    import src.config as config_mod
    from src.harness.verify import VerificationResult
    monkeypatch.setattr(config_mod, "ENABLE_GRAPH_INTERRUPT", True)

    import src.harness.verify as verify_mod

    def _force_reject_once(hit_span, finding, evidence_pkg, contract_text):
        return VerificationResult(status="REJECT", reasons=["forced for interrupt test"], revise_hint=None, evidence_supported=False, dual_mode="dual-agree-reject")

    monkeypatch.setattr(verify_mod, "dual_verify_finding", _force_reject_once)

    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods."
    r1 = client.post("/api/redline", json={"contract_text": contract, "contract_id": "api_interrupt", "engine": "graph"})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["engine"] == "langgraph"
    assert j1["status"] == "pending_human_review"
    assert j1["thread_id"]
    assert j1["interrupt"]["kind"] == "human_review_required"
    assert len(j1["interrupt"]["pending_rejected"]) >= 1
    override_key = j1["interrupt"]["pending_rejected"][0]["override_key"]

    # Resume re-enters human_review_node exactly where it paused -- verify_node never
    # re-runs, so no need to restore dual_verify_finding before calling resume.
    r2 = client.post("/api/harness/resume", json={"contract_id": "api_interrupt", "thread_id": j1["thread_id"], "approve_keys": [override_key]})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["status"] == "complete"
    assert j2["trap_count"] >= 1
    assert any(f.get("verification") == "PASS (human override)" for f in j2["findings"])


def test_redline_graph_engine_reaches_langgraph():
    """End-to-end proof the agentic LangGraph mode is actually reachable through the real
    HTTP API, not just importable in isolation -- this is the exact gap the audit flagged
    (process_contract_graph existed but nothing ever called it)."""
    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods. Notice Period To Terminate Renewal: 30 days."
    r = client.post("/api/redline", json={"contract_text": contract, "contract_id": "api_graph", "engine": "graph"})
    assert r.status_code == 200
    j = r.json()
    assert j["engine"] == "langgraph"
    assert "trap_count" in j and "findings" in j


# --- hardening regressions -------------------------------------------------------------

def test_stream_rejects_path_traversal(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("Renewal Term: renews for 24 months.", encoding="utf-8")
    rel = "../" * 12 + str(outside.with_suffix("")).lstrip("/")
    r = client.get("/api/harness/stream", params={"contract_id": rel})
    assert r.status_code == 422  # rejected by the contract_id pattern, file never read


def test_stream_unknown_fixture_reports_error_event():
    r = client.get("/api/harness/stream", params={"contract_id": "no_such_fixture"})
    assert r.status_code == 200
    assert "fixture not found" in r.text


def test_stream_real_fixture_emits_stages_and_done():
    r = client.get("/api/harness/stream", params={"contract_id": "cuad_00"})
    assert r.status_code == 200
    events = [ln for ln in r.text.splitlines() if ln.startswith("data: ")]
    assert events[-1] == "data: done"
    assert any("Extractor" in e for e in events)


def test_invalid_engine_and_mode_are_rejected():
    body = {"contract_text": "Renewal Term: 24 months."}
    assert client.post("/api/redline", json={**body, "engine": "bogus"}).status_code == 422
    assert client.post("/api/redline", json={**body, "harness_mode": "turbo"}).status_code == 422


def test_whitespace_only_contract_is_422():
    assert client.post("/api/redline", json={"contract_text": "   "}).status_code == 422


def test_redline_timeout_returns_504_without_blocking(monkeypatch):
    import time as _time
    import src.main as main_mod

    def slow(*a, **k):
        _time.sleep(1.0)
        return {}

    monkeypatch.setattr(main_mod, "process_contract_graph", slow)
    monkeypatch.setattr(main_mod, "REDLINE_TIMEOUT_S", 0.1)

    import asyncio
    import httpx

    async def go():
        # A persistent event loop (like uvicorn's): TestClient joins worker threads when it
        # tears its loop down, which would hide whether the timeout fired early.
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
            t0 = _time.perf_counter()
            health = asyncio.create_task(ac.get("/health"))
            r = await ac.post("/api/redline", json={"contract_text": "Renewal Term: 24 months.", "contract_id": "slow"})
            elapsed = _time.perf_counter() - t0
            assert (await health).status_code == 200  # event loop was not blocked meanwhile
            return r, elapsed

    r, elapsed = asyncio.run(go())
    assert r.status_code == 504
    assert elapsed < 0.9  # the timeout actually fired before the work finished


def test_internal_error_does_not_leak_exception_text(monkeypatch):
    import src.main as main_mod

    def boom(*a, **k):
        raise RuntimeError("secret internal detail /etc/passwd")

    monkeypatch.setattr(main_mod, "process_contract_graph", boom)
    r = client.post("/api/redline", json={"contract_text": "Renewal Term: 24 months.", "contract_id": "boom"})
    assert r.status_code == 500
    assert "secret internal detail" not in r.text


def test_negotiation_memory_is_bounded(monkeypatch):
    import src.main as main_mod

    monkeypatch.setattr(main_mod, "_MAX_MEMORIES", 3)
    with main_mod._memories_lock:
        main_mod._memories.clear()
    for i in range(5):
        main_mod._get_memory(f"c{i}", 1)
    assert list(main_mod._memories) == ["c2", "c3", "c4"]
    main_mod._get_memory("c2", 1)  # touching an entry makes it most-recent
    main_mod._get_memory("c5", 1)
    assert list(main_mod._memories) == ["c4", "c2", "c5"]


def test_memory_accumulates_across_turns():
    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods."
    client.post("/api/memory/mem_turns/reset")
    assert client.post("/api/redline", json={"contract_text": contract, "contract_id": "mem_turns", "turn": 1}).status_code == 200
    j = client.get("/api/memory/mem_turns").json()
    assert "P-01" in j["raw"]["open_issues"]


def test_cors_does_not_combine_wildcard_with_credentials():
    r = client.options("/api/redline", headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-credentials") != "true"
