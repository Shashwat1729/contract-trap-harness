"""Graceful-degradation paths of the pipeline: every stage failure yields a well-formed
fallback (never a crash), and fallbacks are queued to the dead-letter file."""
from __future__ import annotations

import json

import pytest

import src.core as core
from src.harness.ingest import Page

TEXT = (
    "Renewal Term: This Agreement shall automatically renew for successive 24 month periods.\n"
    "Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.\n"
)


@pytest.fixture
def reviews_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "REVIEWS_DIR", tmp_path)
    return tmp_path


def _pages():
    return [Page(1, TEXT, 0, len(TEXT))]


def _dead_letters(d):
    return [json.loads(line) for line in (d / "dead_letter.jsonl").read_text().splitlines()]


def _assert_fallback_shape(res):
    assert res["trap_count"] == res["total_proposed"] == 0 and res["findings"] == []
    assert res["fallback"]["status"] == "fallback" and res["fallback"]["sandbox"] is True
    assert set(core.new_llm_stats()) <= set(res["llm_stats"])


def test_extract_failure_returns_fallback_and_dead_letter(reviews_dir, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("extractor exploded")

    monkeypatch.setattr(core, "_retry_extract", boom)
    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x1")
    _assert_fallback_shape(res)
    assert _dead_letters(reviews_dir)[-1]["stage"] == "extract"


def test_risk_stage_failure_returns_fallback(reviews_dir, monkeypatch):
    monkeypatch.setattr(core, "_dedupe_proposed", lambda p: (_ for _ in ()).throw(RuntimeError("risk exploded")))
    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x2")
    _assert_fallback_shape(res)
    assert _dead_letters(reviews_dir)[-1]["stage"] == "risk"


def test_per_hit_risk_and_evidence_failures_are_skipped_not_fatal(reviews_dir, monkeypatch):
    real_assess = core.assess_risk

    def flaky_assess(hit):
        if hit.clause_type == "Renewal Term":
            raise ValueError("bad hit")
        return real_assess(hit)

    monkeypatch.setattr(core, "assess_risk", flaky_assess)
    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x3")
    assert [f["rule_id"] for f in res["findings"]] == ["P-02"]

    monkeypatch.setattr(core, "assess_risk", real_assess)
    monkeypatch.setattr(core, "build_evidence_package", lambda *a, **k: (_ for _ in ()).throw(KeyError("pkg")))
    assert core.process_contract_advanced(TEXT, _pages(), contract_id="x4")["findings"] == []


def test_verify_failure_rejects_instead_of_crashing(reviews_dir, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("verifier down")

    monkeypatch.setattr(core, "dual_verify_finding", boom)
    monkeypatch.setattr(core, "verify_finding", boom)
    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x5")
    assert res["findings"] and all(f["verification"] == "REJECT" for f in res["findings"])
    assert res["trap_count"] == 0 and res["unsupported"] == len(res["findings"])


def test_dual_verify_failure_falls_back_to_single_threshold(reviews_dir, monkeypatch):
    monkeypatch.setattr(core, "dual_verify_finding", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x6")
    assert res["trap_count"] == 2  # single strict verifier still passes the genuine findings


def test_llm_extract_failure_is_non_fatal(reviews_dir, monkeypatch):
    monkeypatch.setattr(core, "ENABLE_LLM_EXTRACT", True)
    monkeypatch.setattr("src.harness.llm_extract.llm_extract_missing_clauses", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("llm")))
    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x7")
    assert res["trap_count"] == 2 and res["llm_extract_generated"] == 0


def test_on_stage_callback_errors_are_swallowed(reviews_dir):
    seen = []

    def cb(stage, detail):
        seen.append(stage)
        raise RuntimeError("slow UI")

    res = core.process_contract_advanced(TEXT, _pages(), contract_id="x8", on_stage=cb)
    assert res["trap_count"] == 2
    assert seen[:3] == ["extract", "risk", "coverage"] and seen[-1] == "route"


def test_graph_invoke_failure_falls_back_to_direct(reviews_dir, monkeypatch):
    import src.harness.graph as g

    monkeypatch.setattr(g, "build_graph", lambda: (_ for _ in ()).throw(RuntimeError("no graph")))
    res = core.process_contract_graph(TEXT, _pages(), contract_id="x9", engine="graph")
    assert res["engine"] == "direct-fallback" and res["trap_count"] == 2


def test_resume_requires_an_interrupted_thread():
    with pytest.raises(ValueError, match="no paused human-review run"):
        core.process_contract_graph(contract_id="never", thread_id="never-interrupted-thread", resume_decision={"approve_keys": []})
    with pytest.raises(ValueError):
        core.process_contract_graph(contract_id="x")  # no text, no resume


def test_thinking_log_is_bounded():
    for i in range(core._THINKING_MAX + 50):
        core._log_thinking("t", i, i, "r")
    assert len(core.THINKING_LOG) == core._THINKING_MAX
    assert len(core.get_thinking_log(10)) == 10
