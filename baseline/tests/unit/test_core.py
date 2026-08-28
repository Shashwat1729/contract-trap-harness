import pytest
from src.core import process, health_check

def test_process_happy():
    assert process("hello") == "baseline processed: hello"

def test_process_empty_raises():
    with pytest.raises(ValueError):
        process("  ")

def test_health():
    assert health_check()["status"] == "ok"
