"""
Cross-cutting e2e — hits live services (run `make run-all` first).
At kickoff, replace with real acceptance-test driven e2e.
"""
import pytest

def test_e2e_placeholder():
    # Placeholder — will call baseline/advanced health at kickoff
    # Example when live:
    #   import httpx
    #   assert httpx.get("http://localhost:8000/health").json()["variant"] == "baseline"
    assert True

@pytest.mark.skip(reason="needs live services — run with make run-all")
def test_live_comparison():
    assert True
