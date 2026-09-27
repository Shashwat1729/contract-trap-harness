"""Thinking-log persistence: opt-in per-entry files, atomic writes, safe snapshot names."""
from __future__ import annotations

import json

from src.core import process_contract_advanced
from src.harness import thinking
from src.harness.ingest import Page


def test_safe_filename_part_strips_traversal():
    assert "/" not in thinking.safe_filename_part("../../etc/passwd")
    assert not thinking.safe_filename_part("..hidden").startswith(".")
    assert thinking.safe_filename_part("") == "unnamed"
    assert len(thinking.safe_filename_part("x" * 500)) == 100


def test_write_json_atomic_leaves_no_temp_files(tmp_path):
    target = tmp_path / "sub" / "log.json"
    assert thinking.write_json_atomic(target, [{"a": 1}])
    assert json.loads(target.read_text()) == [{"a": 1}]
    assert [p.name for p in target.parent.iterdir()] == ["log.json"]


def test_module_logs_are_not_rewritten_per_entry_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("THINKING_LOG_PERSIST", raising=False)
    monkeypatch.setattr(thinking, "REVIEWS_DIR", tmp_path)
    thinking.persist_module_log("thinking_x.json", [{"a": 1}])
    assert not (tmp_path / "thinking_x.json").exists()
    monkeypatch.setenv("THINKING_LOG_PERSIST", "1")
    thinking.persist_module_log("thinking_x.json", [{"a": 1}])
    assert (tmp_path / "thinking_x.json").exists()


def test_snapshot_uses_sanitized_contract_id(tmp_path, monkeypatch):
    import src.core as core_mod

    monkeypatch.setattr(core_mod, "REVIEWS_DIR", tmp_path)
    text = "Renewal Term: renews for 24 months."
    process_contract_advanced(text, [Page(1, text, 0, len(text))], contract_id="../../acme/2024", turn=2)
    written = [p.name for p in tmp_path.iterdir()]
    assert len(written) == 1 and written[0].startswith("thinking_") and written[0].endswith("_t2.json")
    assert "/" not in written[0] and ".." not in written[0]
