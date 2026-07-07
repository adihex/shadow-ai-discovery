from fastapi.testclient import TestClient

from app.main import app


def test_scan_lifecycle_completes():
    """
    Regression test: POST /scan must actually finish. The background task
    previously crashed opening its DB session, leaving scans 'running'
    forever.
    """
    with TestClient(app) as client:
        resp = client.post("/api/scan")
        assert resp.status_code == 200
        scan_id = resp.json()["id"]

        # TestClient executes background tasks before the request returns,
        # so the scan record must already be resolved.
        history = client.get("/api/scan/history").json()
        scan = next(s for s in history if s["id"] == scan_id)
        assert scan["status"] == "completed"
        assert scan["assets_found"] > 0
        assert scan["agents_found"] > 0


def test_agents_endpoints():
    with TestClient(app) as client:
        client.post("/api/scan")
        agents = client.get("/api/agents").json()
        assert len(agents) > 0
        assert all(a["is_ai_agent"] for a in agents)
        assert all(a["confidence_reasons"] for a in agents)

        detail = client.get(f"/api/agents/{agents[0]['id']}")
        assert detail.status_code == 200
        assert detail.json()["id"] == agents[0]["id"]

        assert client.get("/api/agents/does-not-exist").status_code == 404


def test_assets_are_persisted_with_redacted_env_vars():
    with TestClient(app) as client:
        client.post("/api/scan")
        assets = client.get("/api/assets").json()
        assert len(assets) > 0
        for asset in assets:
            for key, value in asset["env_vars"].items():
                if any(t in key.upper() for t in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
                    assert "*" * 10 in value, f"{asset['id']}:{key} not redacted"
