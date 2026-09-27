"""
Offline tests for the infrastructure layers: LLM JSON extraction/repair and key-pool
rotation (litellm mocked -- no network), embeddings, ingest (PDF/TXT/error paths),
negotiation memory, and the router.
"""
from __future__ import annotations

import types

import pytest

import src.harness.embed as embed
import src.harness.keys as keys
import src.harness.llm as llm
from src.harness import ingest
from src.harness.memory import NegotiationMemory, select_harness_mode
from src.harness.router import route_findings
from src.harness.verify import VerificationResult


# --- llm.py: JSON extraction ------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ('{"supported": true, "confidence": 0.8}', {"supported": True, "confidence": 0.8}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('Sure! Here you go: {"a": {"b": 2}} Hope that helps.', {"a": {"b": 2}}),
    ('{"supported": true, "confidence": 0.8, "concern": "The contract spec', {"supported": True, "confidence": 0.8, "concern": "The contract spec"}),
])
def test_extract_json(raw, expected):
    assert llm._extract_json(raw) == expected


def test_extract_json_without_object_raises():
    with pytest.raises(ValueError):
        llm._extract_json("no json here")


def test_repair_truncated_json_gives_up_on_garbage():
    assert llm._repair_truncated_json("not json") is None
    assert llm._repair_truncated_json('{"a": [1, 2') is None


# --- llm.py: call path with a fake litellm ------------------------------------------------

class _FakeRateLimit(Exception):
    pass


def _install_fake_litellm(monkeypatch, behaviour):
    """behaviour(api_key) -> content string, or raises."""
    seen: list = []

    def completion(**kwargs):
        seen.append(kwargs)
        content = behaviour(kwargs.get("api_key"))
        msg = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    fake = types.SimpleNamespace(completion=completion, RateLimitError=_FakeRateLimit, suppress_debug_info=False,
                                 embedding=None)
    monkeypatch.setitem(__import__("sys").modules, "litellm", fake)
    return fake, seen


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(llm, "_EVAL_MOCK", False)
    monkeypatch.setattr(llm, "LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(llm, "_IS_GEMINI", False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(llm._call_one.retry, "wait", lambda *_a, **_k: 0)  # no backoff sleeps


def test_call_llm_json_success(live, monkeypatch):
    _, seen = _install_fake_litellm(monkeypatch, lambda key: '{"supported": false, "confidence": 0.9}')
    out = llm.call_llm_json("sys", "user", mock_response={"supported": True})
    assert out["supported"] is False and out["_ran"] is True and out["_mock"] is False
    assert seen[0]["timeout"] == pytest.approx(float(__import__("os").getenv("LLM_TIMEOUT", "30")))


def test_call_llm_json_degrades_to_mock_on_error(live, monkeypatch):
    def boom(_key):
        raise RuntimeError("provider down")

    _install_fake_litellm(monkeypatch, boom)
    out = llm.call_llm_json("sys", "user", mock_response={"supported": True})
    assert out == {"supported": True, "_mock": True, "_ran": False, "_error": "RuntimeError: provider down"}


def test_call_llm_json_bad_json_degrades(live, monkeypatch):
    _install_fake_litellm(monkeypatch, lambda key: "I refuse to answer in JSON.")
    out = llm.call_llm_json("sys", "user", mock_response={"x": 1})
    assert out["_mock"] is True and out["x"] == 1 and "ValueError" in out["_error"]


def test_gemini_key_pool_rotates_past_rate_limited_key(monkeypatch):
    monkeypatch.setattr(llm, "_EVAL_MOCK", False)
    monkeypatch.setattr(llm, "_IS_GEMINI", True)
    monkeypatch.setattr(llm._call_one.retry, "wait", lambda *_a, **_k: 0)
    monkeypatch.setattr(keys, "_ALL_KEYS", ["key-a", "key-b"])
    keys.reset_for_testing()

    def behaviour(api_key):
        if api_key == "key-a":
            raise _FakeRateLimit("429 GenerateRequestsPerDayPerProjectPerModel")
        return '{"ok": true}'

    _, seen = _install_fake_litellm(monkeypatch, behaviour)
    try:
        out = llm.call_llm_json("s", "u")
        assert out["ok"] is True
        assert "key-a" not in keys.available_keys()  # marked exhausted (daily quota)
        assert keys._EXHAUSTED_UNTIL["key-a"] - __import__("time").time() > 3600
    finally:
        keys.reset_for_testing()


# --- keys.py ----------------------------------------------------------------------------

def test_key_pool_round_robin_and_cooldown(monkeypatch):
    monkeypatch.setattr(keys, "_ALL_KEYS", ["k1", "k2", "k3"])
    keys.reset_for_testing()
    try:
        assert [keys.next_key() for _ in range(4)] == ["k1", "k2", "k3", "k1"]
        keys.mark_exhausted("k2", "per-minute 429")
        assert keys.available_keys() == ["k1", "k3"]
        keys.mark_exhausted("k1")
        keys.mark_exhausted("k3")
        assert keys.next_key() is None
    finally:
        keys.reset_for_testing()


def test_load_keys_dedupes_and_folds_single_vars(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", " a, b ,a,, ")
    monkeypatch.setenv("GEMINI_API_KEY", "b")
    monkeypatch.setenv("GOOGLE_API_KEY", "c")
    monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)
    assert keys._load_keys() == ["a", "b", "c"]


# --- embed.py ---------------------------------------------------------------------------

def test_embed_texts_unavailable_under_eval_mock(monkeypatch):
    monkeypatch.setattr(embed, "_EVAL_MOCK", True)
    assert embed.embed_texts(["x"]) is None
    assert embed.embed_texts([]) == []


def test_embed_texts_batches_and_degrades(monkeypatch):
    monkeypatch.setattr(embed, "_EVAL_MOCK", False)
    monkeypatch.setattr(embed, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(embed._embed_one.retry, "wait", lambda *_a, **_k: 0)
    monkeypatch.setattr(keys, "_ALL_KEYS", [])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    batches: list = []

    def embedding(model, input, timeout, **kw):
        batches.append(list(input))
        return types.SimpleNamespace(data=[{"embedding": [float(len(t))]} for t in input])

    fake = types.SimpleNamespace(embedding=embedding, RateLimitError=_FakeRateLimit, suppress_debug_info=False)
    monkeypatch.setitem(__import__("sys").modules, "litellm", fake)
    out = embed.embed_texts(["a", "bb", "ccc"], batch_size=2)
    assert out == [[1.0], [2.0], [3.0]] and [len(b) for b in batches] == [2, 1]

    def broken(**kw):
        raise RuntimeError("quota")

    fake.embedding = broken
    assert embed.embed_texts(["a"]) is None  # never raises


# --- ingest.py --------------------------------------------------------------------------

def _minimal_pdf(lines_per_page: list[str]) -> bytes:
    """A tiny, valid, text-bearing PDF (Helvetica, one text line per page)."""
    objs: list[bytes] = []
    n_pages = len(lines_per_page)
    page_ids = [4 + 2 * i for i in range(n_pages)]
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [" + b" ".join(f"{p} 0 R".encode() for p in page_ids) + f"] /Count {n_pages} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, line in enumerate(lines_per_page):
        stream = f"BT /F1 12 Tf 72 720 Td ({line}) Tj ET".encode()
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_ids[i] + 1} 0 R >>".encode())
        objs.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_pdf_ingest_preserves_real_pages(tmp_path):
    path = tmp_path / "c.pdf"
    path.write_bytes(_minimal_pdf(["Renewal Term: 24 months.", "Notice: 30 days."]))
    text, pages = ingest.extract_text_with_pages(path)
    assert [p.num for p in pages] == [1, 2]
    assert "Renewal Term" in pages[0].text and "Notice" in pages[1].text
    assert all(text[p.start:p.end] == p.text for p in pages)
    assert ingest.offset_to_page_line(text.index("Notice"), pages, text) == (2, 1)


def test_txt_ingest_and_missing_file(tmp_path):
    path = tmp_path / "c.txt"
    path.write_text("line one\nline two\n" * 300, encoding="utf-8")
    text, pages = ingest.extract_text_with_pages(path, chars_per_page=1000)
    assert len(pages) == -(-len(text) // 1000)
    assert ingest.offset_to_page_line(1005, pages, text)[0] == 2
    fb_text, fb_pages = ingest.extract_text_with_pages(tmp_path / "missing.txt")
    assert fb_text.startswith("[INGEST FALLBACK: FileNotFoundError") and len(fb_pages) == 1


def test_offset_past_end_maps_to_last_page():
    text = "a" * 30
    pages = [ingest.Page(1, text[:20], 0, 20), ingest.Page(2, text[20:], 20, 30)]
    assert ingest.offset_to_page_line(10_000, pages, text) == (2, 1)
    assert ingest.offset_to_page_line(0, [], "") == (1, 1)


# --- memory.py / router.py --------------------------------------------------------------

def test_negotiation_memory_tracks_high_risk_issues_once():
    mem = NegotiationMemory(contract_id="c", turn=1)
    assert mem.to_context() == "No prior negotiation memory."
    findings = [{"rule_id": "P-01", "risk": "High"}, {"rule_id": "P-01", "risk": "High"}, {"rule_id": "P-06", "risk": "Medium"}]
    mem.update_from_findings(findings, turn=2)
    assert mem.turn == 2 and mem.open_issues == ["P-01"] and len(mem.prior_findings) == 3
    mem.accepted_positions.append("P-06 Delaware")
    ctx = mem.to_context()
    assert "Open issues: P-01" in ctx and "Accepted: P-06 Delaware" in ctx


@pytest.mark.parametrize("model,requested,expected", [
    ("gpt-4o-mini", "strict", "strict"),
    ("gemini/gemini-2.5-flash", "auto", "light"),
    ("claude-haiku-4-5", "auto", "balanced"),
    ("some-local-model", "auto", "balanced"),
    ("gpt-4o-mini", "nonsense", "light"),
])
def test_select_harness_mode(model, requested, expected):
    assert select_harness_mode(model, requested) == expected


def test_router_routes_everything_to_human_review():
    ok = VerificationResult("PASS", [], None, True, "dual-agree-pass")
    bad = {"status": "REJECT", "reasons": ["x"], "dual_mode": "dual-agree-reject"}
    out = route_findings([{"clause_type": "A"}, {"clause_type": "B"}], [ok, bad])
    assert [(r.route, r.verification) for r in out] == [("human_review", "PASS"), ("human_review", "REJECT")]
    assert out[1].reasons == ["x"]
