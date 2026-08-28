from fastapi.testclient import TestClient
from src.main import app, ADVANCED_FEATURES

client = TestClient(app)

def test_health_has_features():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["variant"] == "advanced"
    assert "features" in j
    assert len(j["features"]) >= 1

def test_example_verified():
    r = client.get("/api/example", params={"q": "hello"})
    assert r.status_code == 200
    assert r.json()["verified"] is True

def test_empty_payload_fallback():
    r = client.post("/api/example", json={})
    assert r.status_code == 200
    assert r.json().get("fallback")
