"""
Regression tests for LLM cross-check verdict parsing and routing, provider-aware
availability, and exact offsets from llm_extract._find_verbatim.
"""
from __future__ import annotations

import pytest

import src.harness.llm as llm_mod
import src.harness.llm_verify as lv
from src.harness import llm_extract as le
from src.harness.risk import RiskFinding
from src.harness.verify import VerificationResult


def _finding(conf: float = 0.8) -> RiskFinding:
    return RiskFinding("Renewal Term", "High", "P-01", "Acme", "change", "why", conf, "span", 1, 1)


def _pass(dual_mode: str = "dual-agree-pass") -> VerificationResult:
    return VerificationResult(status="PASS", reasons=[], revise_hint=None, evidence_supported=True, dual_mode=dual_mode)


@pytest.fixture
def live_llm(monkeypatch):
    """Pretend a provider is available and let each test script the model's JSON reply."""
    reply: dict = {}
    monkeypatch.setattr(lv, "llm_available", lambda: True)
    monkeypatch.setattr(lv, "call_llm_json", lambda *a, **k: {"_ran": True, "_mock": False, **reply})
    return reply


@pytest.mark.parametrize("raw,expected", [
    (False, False), ("false", False), ("False", False), ("no", False), (0, False),
    (True, True), ("true", True), ("yes", True), (1, True),
    (None, None), ("maybe", None), ([], None),
])
def test_supported_is_parsed_strictly(live_llm, raw, expected):
    live_llm.update({"supported": raw, "confidence": 0.9})
    assert lv.llm_verify_finding("span", _finding(), {}).supported is expected


@pytest.mark.parametrize("raw,expected", [
    (0.7, 0.7), ("0.7", 0.7), (70, 0.7), ("70%", 0.7), (None, None), ("high", None), (-1, 0.0),
])
def test_confidence_is_parsed_and_clamped(live_llm, raw, expected):
    live_llm.update({"supported": True, "confidence": raw})
    got = lv.llm_verify_finding("span", _finding(), {}).confidence
    assert got == (pytest.approx(expected) if expected is not None else None)


def test_string_false_from_model_downgrades_pass(live_llm):
    """The model said "false" (a string): this used to be read as supported=True."""
    live_llm.update({"supported": "false", "confidence": "0.9", "concern": "wrong clause"})
    ver, stats = _pass("dual-disagree"), lv.new_llm_stats()
    lv.llm_cross_check("span", _finding(0.7), {}, ver, stats, enabled=True, skip_confidence=0.85)
    assert ver.status == "REJECT" and stats["flagged"] == 1
    assert any("wrong clause" in r for r in ver.reasons)


def test_unsupported_without_confidence_is_flagged_not_confirmed(live_llm):
    live_llm.update({"supported": False})
    ver, stats = _pass("dual-disagree"), lv.new_llm_stats()
    lv.llm_cross_check("span", _finding(0.7), {}, ver, stats, enabled=True, skip_confidence=0.85)
    assert ver.status == "REJECT" and stats["flagged"] == 1 and stats["confirmed"] == 0


def test_low_confidence_unsupported_does_not_downgrade(live_llm):
    live_llm.update({"supported": False, "confidence": 0.3})
    ver, stats = _pass("dual-disagree"), lv.new_llm_stats()
    lv.llm_cross_check("span", _finding(0.7), {}, ver, stats, enabled=True, skip_confidence=0.85)
    assert ver.status == "PASS" and stats["confirmed"] == 1


def test_unparseable_verdict_is_inconclusive_and_keeps_pass(live_llm):
    live_llm.update({"supported": "perhaps", "confidence": 0.9})
    ver, stats = _pass("dual-disagree"), lv.new_llm_stats()
    lv.llm_cross_check("span", _finding(0.7), {}, ver, stats, enabled=True, skip_confidence=0.85)
    assert ver.status == "PASS" and stats["inconclusive"] == 1 and stats["confirmed"] == 0


def test_cross_check_routing(monkeypatch):
    calls = []

    def fake(*a, **k):
        calls.append(1)
        return lv.LLMVerifyResult(ran=True, supported=True, confidence=0.9, concern="", mock=False)

    stats = lv.new_llm_stats()
    # high confidence + dual-agree-pass -> skipped, no call
    assert lv.llm_cross_check("s", _finding(0.9), {}, _pass(), stats, enabled=True, skip_confidence=0.85, verify_fn=fake) is None
    # disabled / already REJECTed -> no call
    lv.llm_cross_check("s", _finding(0.5), {}, _pass(), stats, enabled=False, skip_confidence=0.85, verify_fn=fake)
    rej = VerificationResult(status="REJECT", reasons=["x"], revise_hint=None, evidence_supported=False)
    lv.llm_cross_check("s", _finding(0.5), {}, rej, stats, enabled=True, skip_confidence=0.85, verify_fn=fake)
    # low confidence -> real call
    lv.llm_cross_check("s", _finding(0.5), {}, _pass(), stats, enabled=True, skip_confidence=0.85, verify_fn=fake)
    assert len(calls) == 1
    assert stats["skipped_high_confidence"] == 1 and stats["ran"] == 1 and stats["confirmed"] == 1


def test_cross_check_survives_verify_exception():
    def boom(*a, **k):
        raise RuntimeError("network down")

    ver, stats = _pass("dual-disagree"), lv.new_llm_stats()
    assert lv.llm_cross_check("s", _finding(0.5), {}, ver, stats, enabled=True, skip_confidence=0.85, verify_fn=boom) is None
    assert ver.status == "PASS" and stats["skipped"] == 1


@pytest.mark.parametrize("model,env,expected", [
    ("gpt-4o-mini", {"OPENAI_API_KEY": "k"}, True),
    ("gpt-4o-mini", {"ANTHROPIC_API_KEY": "k"}, False),   # wrong provider's key
    ("claude-haiku-4-5-20251001", {"ANTHROPIC_API_KEY": "k"}, True),
    ("anthropic/claude-x", {"OPENAI_API_KEY": "k"}, False),
    ("mistral/mistral-small", {"OPENAI_API_KEY": "k"}, True),  # unknown provider: any key
    ("mistral/mistral-small", {}, False),
])
def test_llm_available_requires_matching_provider_key(monkeypatch, model, env, expected):
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY", "GEMINI_API_KEYS", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(llm_mod, "_EVAL_MOCK", False)
    monkeypatch.setattr(llm_mod, "LLM_MODEL", model)
    monkeypatch.setattr(llm_mod, "_IS_GEMINI", model.startswith("gemini/"))
    assert llm_mod.llm_available() is expected


def test_llm_available_false_under_eval_mock(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(llm_mod, "_EVAL_MOCK", True)
    assert llm_mod.llm_available() is False


def test_find_verbatim_whitespace_tolerant_returns_exact_end():
    text = "Preamble.\nThe Vendor shall   provide\ntransition assistance for thirty days. Next clause."
    span = "The Vendor shall provide transition assistance for thirty days."
    start, end = le._find_verbatim(text, span)
    assert text[start:end] == "The Vendor shall   provide\ntransition assistance for thirty days."


def test_find_verbatim_rejects_short_non_exact_and_reordered():
    text = "Either party may terminate this Agreement for convenience."
    assert le._find_verbatim(text, "party  may\nterm") is None  # < 15 chars, not exact
    assert le._find_verbatim(text, "terminate this Agreement may party for convenience") is None
