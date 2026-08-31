"""
Dashboard smoke test -- runs app/streamlit_app.py for real via Streamlit's own
AppTest harness and asserts it does not raise.

Why this exists: the dashboard previously crashed on every single load with
`NameError: name 'tc2' is not defined` (a stray duplicate block referencing
columns that were never created in that scope) -- and nothing caught it, because
nothing had ever actually executed the script end to end. `python -m py_compile`
and `ast.parse` both passed the whole time; they only check syntax, not that the
script runs. Run this with `python -m pytest app/tests` from the repo root.
"""
import os

import pytest

pytest.importorskip("streamlit", reason="streamlit not installed")

os.environ.setdefault("EVAL_MOCK", "1")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py")


def test_dashboard_loads_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=60)
    assert not at.exception, f"dashboard raised on load: {at.exception}"


def test_dashboard_has_all_seven_tabs():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=60)
    assert not at.exception
    assert len(at.tabs) == 7, f"expected 7 tabs, found {len(at.tabs)}"


def test_harness_panel_loads_with_contract_and_runs_graph_engine():
    """Regression test for the LangGraph wiring: load a contract into session state,
    switch the engine radio to 'graph', click Run Harness, and assert the real pipeline
    executes end to end with no exception -- exercising the exact button-click code path
    a judge would hit in a live demo, not just the module-import path."""
    at = AppTest.from_file(APP_PATH)
    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods. Notice Period To Terminate Renewal: 30 days."
    at.session_state["contract_text"] = contract
    at.session_state["contract_id"] = "smoke_test_01"
    at.session_state["meta"] = {"trap_gold": []}
    at.run(timeout=60)
    assert not at.exception

    radio = at.radio(key="harness_engine_choice")
    radio.set_value("graph")
    at.button(key="harness_run").click()
    at.run(timeout=90)

    assert not at.exception, f"harness run raised: {at.exception}"
    assert not list(at.error), f"harness run rendered an error: {[e.value for e in at.error]}"


def test_harness_panel_llm_extract_checkbox_badge_reflects_actual_run_state():
    """
    CHANGELOG #22 audit finding: the LLM-generator badge was reading the LIVE
    ENABLE_LLM_EXTRACT config value AFTER the run's try/finally had already
    restored it to its pre-run default, so a judge who ticked the checkbox and
    ran it would still see "OFF" on the badge -- the exact bug class CHANGELOG
    #21 already found once for the interrupt-resume toggle. Drives the real
    checkbox through AppTest (EVAL_MOCK=1, so the LLM itself never actually
    runs, but the wiring/badge-read path is real) and asserts the badge shows
    ON, not the always-restored-to-off value.
    """
    at = AppTest.from_file(APP_PATH)
    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods."
    at.session_state["contract_text"] = contract
    at.session_state["contract_id"] = "smoke_llm_extract_01"
    at.session_state["meta"] = {"trap_gold": []}
    at.run(timeout=60)
    assert not at.exception

    at.checkbox(key="harness_enable_llm_extract").set_value(True)
    at.button(key="harness_run").click()
    at.run(timeout=90)

    assert not at.exception, f"run raised: {at.exception}"
    assert any("LLM-generator ON" in i.value for i in at.info), (
        "badge did not show ON despite the checkbox being checked for this run "
        f"-- info panels were: {[i.value for i in at.info]}"
    )


def test_harness_panel_real_interrupt_and_resume_through_ui(monkeypatch):
    """CHANGELOG #21: drives the real human-in-the-loop interrupt/resume cycle through
    the actual dashboard UI (checkbox -> Run Harness -> approve-override checkbox ->
    Resume button), not just the underlying API/graph mechanics tested elsewhere. Forces
    a REJECT via a monkeypatched dual_verify_finding so the scenario is deterministic."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    import advanced.src.harness.verify as verify_mod
    from advanced.src.harness.verify import VerificationResult

    def _force_reject(hit_span, finding, evidence_pkg, contract_text):
        return VerificationResult(status="REJECT", reasons=["forced for dashboard interrupt test"], revise_hint=None, evidence_supported=False, dual_mode="dual-agree-reject")

    monkeypatch.setattr(verify_mod, "dual_verify_finding", _force_reject)

    at = AppTest.from_file(APP_PATH)
    contract = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods."
    at.session_state["contract_text"] = contract
    at.session_state["contract_id"] = "smoke_interrupt_01"
    at.session_state["meta"] = {"trap_gold": []}
    at.run(timeout=60)
    assert not at.exception

    at.radio(key="harness_engine_choice").set_value("graph")
    at.checkbox(key="harness_enable_interrupt").set_value(True)
    at.button(key="harness_run").click()
    at.run(timeout=90)
    assert not at.exception, f"run raised: {at.exception}"
    assert any("Human review required" in w.value for w in at.warning), "pending-review panel did not render"

    override_checkboxes = [cb for cb in at.checkbox if cb.key and cb.key.startswith("override_")]
    assert len(override_checkboxes) >= 1, "no override checkbox rendered for the forced REJECT"
    override_checkboxes[0].set_value(True)
    at.button(key="resume_harness_btn").click()
    at.run(timeout=60)

    assert not at.exception, f"resume raised: {at.exception}"
    assert any("Resumed after human review" in s.value for s in at.success), "resume did not render the human-override confirmation"
