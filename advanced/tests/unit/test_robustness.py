"""
Seeded robustness sweep: mutated real fixtures (whitespace noise, case changes, unicode,
random truncation, oversized input) through both engines. Invariants, not snapshots:
never crash, counters consistent, every approved citation genuinely occurs in the text.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

import pytest

from src.core import process_contract_graph
from src.harness.ingest import Page

FIXTURES = sorted((Path(__file__).parents[3] / "shared" / "fixtures").glob("*/*.txt"))


def _pages(text: str, cpp: int = 2500) -> list[Page]:
    return [Page(num=i // cpp + 1, text=text[i:i + cpp], start=i, end=min(i + cpp, len(text)))
            for i in range(0, len(text), cpp)] or [Page(1, text, 0, len(text))]


def _mutate(text: str, rng: random.Random) -> str:
    ops = [
        lambda t: re.sub(r" ", lambda _m: rng.choice([" ", "  ", "\n", " \t "]), t),
        lambda t: t.upper(),
        lambda t: t.replace("-", "–").replace('"', "“"),
        lambda t: t[: rng.randint(1, max(1, len(t)))],
        lambda t: " ".join(t.split(" ")),
        lambda t: t + "\n\n" + "Ünïcödé 契約 条項 😀 " * 50,
    ]
    for op in rng.sample(ops, k=rng.randint(1, 3)):
        text = op(text)
    return text if text.strip() else "x"


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def _check(res: dict, text: str) -> None:
    assert res["evidence_supported"] + res["unsupported"] == res["total_proposed"] == len(res["findings"])
    assert res["trap_count"] == len(res["approved_candidates"])
    assert 0.0 <= res["surgical_rate"] <= 1.0
    norm_text = _norm(text)
    for f in res["approved_candidates"]:
        assert f["verification"].startswith("PASS")
        assert _norm(f["span_text"]) in norm_text  # approved citations are real text
        assert f["page"] >= 1 and f["line"] >= 1


@pytest.mark.parametrize("seed", range(12))
def test_mutated_fixtures_hold_invariants(seed):
    rng = random.Random(seed)
    path = FIXTURES[seed % len(FIXTURES)]
    text = _mutate(path.read_text(encoding="utf-8"), rng)
    engine = "graph" if seed % 3 == 0 else "direct"
    res = process_contract_graph(text, _pages(text), contract_id=f"fuzz_{seed}", engine=engine)
    assert res["engine"] in ("direct", "langgraph")
    _check(res, text)


def test_oversized_input_is_truncated_not_rejected():
    from src.config import MAX_CHARS

    base = FIXTURES[0].read_text(encoding="utf-8")
    text = (base + "\n") * (MAX_CHARS // max(len(base), 1) + 2)
    assert len(text) > MAX_CHARS
    res = process_contract_graph(text, _pages(text), contract_id="huge", engine="direct")
    _check(res, text[:MAX_CHARS])


@pytest.mark.parametrize("text", ["x", "​​Renewal", "(((((((", "Renewal Term: " + "9" * 5000 + " months"])
def test_degenerate_inputs_do_not_crash(text):
    _check(process_contract_graph(text, _pages(text), contract_id="degenerate", engine="direct"), text)
