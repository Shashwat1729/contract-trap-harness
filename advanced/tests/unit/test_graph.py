"""
Tests for the LangGraph agentic harness (src.harness.graph).

Before this file existed, graph.py had zero test coverage -- which is exactly how a
broken import (evidence_node's `from advanced.src.core import ...`, wrong for this
project's actual package path `src.harness.graph`) went unnoticed: nothing ever called
it, so nothing ever failed. These tests exercise the graph for real, end to end and
node by node, so a regression here is caught the same way core.py's are.
"""
import pytest

from src.harness.ingest import Page

pytest.importorskip("langgraph", reason="langgraph not installed")

from src.harness import graph as g  # noqa: E402
from src.harness.risk import RiskFinding  # noqa: E402
from src.harness.extract import ClauseHit  # noqa: E402
from src.harness.verify import VerificationResult  # noqa: E402


TRAP_CONTRACT = """
SaaS Agreement
Renewal Term: This Agreement shall automatically renew for successive 24 month periods.
Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.
Cap On Liability: Liability is capped at 12 months fees, except carve-outs for data breach are excluded from cap and not subject to limitation.
"""


def _pages(text: str) -> list[Page]:
    return [Page(num=1, text=text, start=0, end=len(text))]


def test_langgraph_available():
    assert g.LANGGRAPH_AVAILABLE is True, "langgraph is a declared dependency (advanced/requirements.txt) -- must actually be importable"


def test_build_graph_has_all_nodes():
    graph = g.build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    for expected in ("extract", "risk", "evidence", "verify", "revise", "human_review"):
        assert expected in node_names, f"node {expected!r} missing from compiled graph"


def test_graph_mode_matches_direct_mode_on_trap_contract(monkeypatch):
    """Graph mode must not be a weaker path than the direct pipeline -- same contract,
    same trap_count, same dual_stats shape."""
    import src.core as core
    from src.core import process_contract_graph, process_contract_advanced

    monkeypatch.setattr(core, "ENABLE_LANGGRAPH", True)
    pages = _pages(TRAP_CONTRACT)
    res_graph = process_contract_graph(TRAP_CONTRACT, pages, contract_id="graph_test", turn=1, harness_mode="balanced")
    res_direct = process_contract_advanced(TRAP_CONTRACT, pages, contract_id="direct_test", turn=1, harness_mode="balanced")

    assert res_graph["trap_count"] == res_direct["trap_count"]
    assert res_graph["total_proposed"] == res_direct["total_proposed"]
    assert res_graph["dual_stats"] == res_direct["dual_stats"]
    assert 0.0 <= res_graph["surgical_rate"] <= 1.0
    stages = [t.get("stage") for t in res_graph["thinking"]]
    assert "extract" in stages and "risk" in stages and "verify" in stages and "human_review" in stages


def test_repeated_graph_calls_on_same_contract_id_do_not_leak_state(monkeypatch):
    """CHANGELOG #21 regression: build_graph()'s checkpointer is now a process-lifetime
    singleton (needed for real interrupt/resume). Verified directly that this makes
    thread_id reuse dangerous: HarnessState's Annotated[..., operator.add] accumulator
    fields (clause_hits, thinking) silently carried a PRIOR run's values into a second
    run on the same thread_id. Fixed by giving every fresh (non-resume) call its own
    unique thread_id (contract_id is no longer used as thread_id directly) -- this test
    proves two back-to-back calls on the same contract_id stay fully independent."""
    import src.core as core
    from src.core import process_contract_graph

    monkeypatch.setattr(core, "ENABLE_LANGGRAPH", True)
    c1 = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods."
    r1 = process_contract_graph(c1, _pages(c1), contract_id="leak_regression_test", turn=1)
    types1 = {f["clause_type"] for f in r1["findings"]}
    assert "Renewal Term" in types1

    c2 = "Governing Law: This Agreement is governed by the laws of Delaware."
    r2 = process_contract_graph(c2, _pages(c2), contract_id="leak_regression_test", turn=1)
    types2 = {f["clause_type"] for f in r2["findings"]}
    assert "Renewal Term" not in types2, "second run on the same contract_id must not inherit findings from the first run"


def test_graph_mode_off_falls_back_to_direct(monkeypatch):
    import src.core as core

    monkeypatch.setattr(core, "ENABLE_LANGGRAPH", False)
    pages = _pages(TRAP_CONTRACT)
    res = core.process_contract_graph(TRAP_CONTRACT, pages, contract_id="off_test", turn=1)
    assert res["variant"] == "advanced"


def _fake_finding(proposed_change: str = "short fix") -> RiskFinding:
    return RiskFinding(
        clause_type="Renewal Term", risk="High", rule_id="P-01", precedent_id="PR-01",
        proposed_change=proposed_change, rationale="test", confidence=0.9,
        evidence_contract_span="Renewal Term: 24 months", evidence_page=1, evidence_line=1,
    )


def _fake_hit() -> ClauseHit:
    return ClauseHit(
        clause_type="Renewal Term", span_text="Renewal Term: 24 months",
        start=0, end=24, page=1, line=1, confidence=0.9, match_kind="pattern",
    )


def test_shorten_surgical_actually_shortens():
    long_text = "This is a very long block edit clause. " * 20
    assert len(long_text) > 280
    short = g._shorten_surgical(long_text, limit=280)
    assert len(short) <= 281  # allow the trailing ellipsis/period
    assert short != long_text


def test_shorten_surgical_noop_when_already_short():
    text = "Cap liability at 12 months fees."
    assert g._shorten_surgical(text) == text


def test_revise_node_shortens_block_edit_finding():
    """A REJECT for 'not surgical' must produce a genuinely different (shorter)
    proposed_change on revise -- not a relabeling of the same output."""
    long_change = "Replace with the following much longer surgical redline text. " * 10
    hit = _fake_hit()
    finding = _fake_finding(proposed_change=long_change)
    pkg = {"contract_span": hit.span_text}
    ver = VerificationResult(status="REJECT", reasons=["proposed change is block edit (650 chars) not surgical - split into smaller edits"], revise_hint="shorten", evidence_supported=False)

    state = {"proposed": [(hit, finding, pkg)], "verification_results": [ver], "retry_count": 0, "contract_text": TRAP_CONTRACT}
    result = g.revise_node(state)

    assert result["retry_count"] == 1
    revised_hit, revised_finding, revised_pkg = result["proposed"][0]
    assert len(revised_finding.proposed_change) < len(long_change)
    assert revised_finding.proposed_change != long_change


def test_revise_node_leaves_passed_findings_untouched():
    hit = _fake_hit()
    finding = _fake_finding()
    pkg = {"contract_span": hit.span_text}
    ver = VerificationResult(status="PASS", reasons=[], revise_hint=None, evidence_supported=True)

    state = {"proposed": [(hit, finding, pkg)], "verification_results": [ver], "retry_count": 0, "contract_text": TRAP_CONTRACT}
    result = g.revise_node(state)

    _, revised_finding, revised_pkg = result["proposed"][0]
    assert revised_finding is finding
    assert revised_pkg is pkg


def test_should_revise_routes_to_revise_on_fresh_reject_with_hint():
    ver = VerificationResult(status="REJECT", reasons=["x"], revise_hint="retry", evidence_supported=False)
    state = {"verification_results": [ver], "retry_count": 0}
    assert g.should_revise(state) == "revise"


def test_should_revise_routes_to_human_review_after_one_retry():
    ver = VerificationResult(status="REJECT", reasons=["x"], revise_hint="retry", evidence_supported=False)
    state = {"verification_results": [ver], "retry_count": 1}
    assert g.should_revise(state) == "human_review"


def test_should_revise_routes_to_human_review_when_no_hint():
    ver = VerificationResult(status="REJECT", reasons=["x"], revise_hint=None, evidence_supported=False)
    state = {"verification_results": [ver], "retry_count": 0}
    assert g.should_revise(state) == "human_review"


def test_human_review_real_interrupt_and_resume_override(monkeypatch):
    """CHANGELOG #21: real langgraph interrupt()/Command(resume=...) cycle, not mocked --
    exercises the actual pause/resume mechanism a human reviewer would drive, wrapping
    human_review_node in its own tiny checkpointed graph so the test controls exactly
    which finding is REJECTed without needing a fixture that naturally produces one."""
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    import src.config as config_mod

    monkeypatch.setattr(config_mod, "ENABLE_GRAPH_INTERRUPT", True)

    hit = ClauseHit(clause_type="Renewal Term", span_text="Renewal Term: 24 months", start=0, end=23, page=1, line=1, confidence=0.9, match_kind="pattern")
    finding = RiskFinding(clause_type="Renewal Term", risk="High", rule_id="P-01", precedent_id="PR-01", proposed_change="short edit", rationale="test", confidence=0.9, evidence_contract_span="Renewal Term: 24 months", evidence_page=1, evidence_line=1)
    pkg = {"contract_span": "Renewal Term: 24 months", "contract_page": 1, "playbook_rule": "P-01", "precedent": {"id": "PR-01"}, "confidence": 0.9}
    ver = VerificationResult(status="REJECT", reasons=["test reject reason"], revise_hint=None, evidence_supported=False, dual_mode="dual-agree-reject")

    builder = StateGraph(g.HarnessState)
    builder.add_node("human_review", g.human_review_node)
    builder.add_edge(START, "human_review")
    builder.add_edge("human_review", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "interrupt_test"}}

    init_state = {"contract_id": "interrupt_test", "verified": [(hit, finding, pkg, ver)], "llm_results": [None], "stage_latency_ms": {}}
    result1 = graph.invoke(init_state, config=config)

    assert "__interrupt__" in result1, "graph must actually pause, not finish, when a REJECT is pending"
    payload = result1["__interrupt__"][0].value
    assert payload["kind"] == "human_review_required"
    assert len(payload["pending_rejected"]) == 1
    override_key = payload["pending_rejected"][0]["override_key"]
    assert override_key == "Renewal Term|P-01|1|1|0"

    result2 = graph.invoke(Command(resume={"approve_keys": [override_key]}), config=config)
    assert "__interrupt__" not in result2, "resume must actually finish the paused node, not re-interrupt"
    assert len(result2["approved"]) == 1
    assert result2["approved"][0]["human_override"] is True
    assert result2["approved"][0]["verification"] == "PASS (human override)"
    assert result2["rejected"] == []


def test_human_review_interrupt_skipped_when_flag_off(monkeypatch):
    """ENABLE_GRAPH_INTERRUPT=0 (the default) must behave exactly as before this feature --
    REJECTed findings stay REJECTed, no pause, no behavior change for the default path."""
    import src.config as config_mod
    monkeypatch.setattr(config_mod, "ENABLE_GRAPH_INTERRUPT", False)

    hit = ClauseHit(clause_type="Renewal Term", span_text="Renewal Term: 24 months", start=0, end=23, page=1, line=1, confidence=0.9, match_kind="pattern")
    finding = RiskFinding(clause_type="Renewal Term", risk="High", rule_id="P-01", precedent_id="PR-01", proposed_change="short edit", rationale="test", confidence=0.9, evidence_contract_span="Renewal Term: 24 months", evidence_page=1, evidence_line=1)
    pkg = {"contract_span": "Renewal Term: 24 months", "contract_page": 1, "playbook_rule": "P-01", "precedent": {"id": "PR-01"}, "confidence": 0.9}
    ver = VerificationResult(status="REJECT", reasons=["test reject reason"], revise_hint=None, evidence_supported=False, dual_mode="dual-agree-reject")

    state = {"contract_id": "no_interrupt_test", "verified": [(hit, finding, pkg, ver)], "llm_results": [None], "stage_latency_ms": {}}
    out = g.human_review_node(state)
    assert len(out["rejected"]) == 1
    assert len(out["approved"]) == 0


def test_evidence_node_import_path_resolves():
    """Regression test for the exact bug this file exists to catch: evidence_node used to
    import `advanced.src.core` (wrong package path -- ModuleNotFoundError, silently
    swallowed) instead of a relative import. Confirms it now actually populates output."""
    state = {"contract_text": TRAP_CONTRACT, "pages": _pages(TRAP_CONTRACT), "clause_hits": []}
    result = g.evidence_node(state)
    assert "trap_interactions" in result
    assert "coverage_gaps" in result
    assert isinstance(result["coverage_gaps"], list) and len(result["coverage_gaps"]) > 0  # no hits -> every playbook rule is a gap
