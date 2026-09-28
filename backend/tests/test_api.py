"""API tests against a real Postgres (skipped if the database isn't running)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import cv_store
from app.db import engine
from app.main import app, get_llm

from .fakes import FakeLLM, fake_embed

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception:
    pytest.skip("Postgres isn't running (start it with: docker compose up db -d)", allow_module_level=True)

CV = "Jane Doe\n- Built Python APIs with FastAPI\n- Ran services on Kubernetes in production"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cv_store, "embed", fake_embed)
    app.dependency_overrides[get_llm] = lambda: FakeLLM(fact_problems_per_check=[[]])
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_analyze_then_track_an_application(client):
    assert client.put("/api/profile", json={"cv_text": CV}).status_code == 200

    r = client.post("/api/applications/analyze", json={"job_text": "Acme needs a Python dev"})
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]
    assert r.json()["company"] == "Acme"
    assert r.json()["match_score"] == 80
    assert r.json()["status"] == "saved"

    r = client.patch(f"/api/applications/{app_id}", json={"status": "applied", "notes": "Sent Monday"})
    assert r.json()["status"] == "applied"
    assert r.json()["notes"] == "Sent Monday"

    assert any(a["id"] == app_id for a in client.get("/api/applications").json())
    assert client.delete(f"/api/applications/{app_id}").status_code == 204
    assert client.get(f"/api/applications/{app_id}").status_code == 404


def test_analyze_needs_a_job(client):
    assert client.post("/api/applications/analyze", json={}).status_code == 422


def test_invalid_status_is_rejected(client):
    client.put("/api/profile", json={"cv_text": CV})
    app_id = client.post("/api/applications/analyze", json={"job_text": "x"}).json()["id"]
    assert client.patch(f"/api/applications/{app_id}", json={"status": "ghosted"}).status_code == 422
