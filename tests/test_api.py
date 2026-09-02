import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db


@pytest.fixture(autouse=True)
def setup_api_db(tmp_path):
    db.reset_engine()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_api.db"
    db.init_db()
    yield
    db.reset_engine()


client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_status_endpoint():
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "stats" in data


def test_root_dashboard_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "LH2 AI LABS" in resp.text
    assert "Company Intelligence Agent" in resp.text


def test_get_results_empty():
    resp = client.get("/results")
    assert resp.status_code == 200
    assert resp.json() == []
