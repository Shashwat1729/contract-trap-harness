from src.core import process
from src.verify import verify

def test_advanced_graceful_empty():
    # advanced doesn't raise — graceful fallback
    result = process("  ")
    assert "empty query" in result

def test_advanced_happy():
    assert "verified" in process("hello")

def test_verify():
    assert verify("some output")["ok"] is True
    assert verify("")["ok"] is False
