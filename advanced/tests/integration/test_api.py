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
