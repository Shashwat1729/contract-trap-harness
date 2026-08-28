from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["variant"] == "baseline"

def test_example_get():
    r = client.get("/api/example", params={"q": "test"})
    assert r.status_code == 200
    assert "baseline processed" in r.json()["result"]

def test_example_post():
    r = client.post("/api/example", json={"q": "hi"})
    assert r.status_code == 200
    assert r.json()["variant"] == "baseline"
