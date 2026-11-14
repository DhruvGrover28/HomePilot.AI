from fastapi.testclient import TestClient

from app.db import initialize_database
from app.main import app


def test_agent_run_routes_domains_and_persists_result():
    initialize_database()
    with TestClient(app) as client:
        response = client.post(
            "/api/agents/runs",
            json={"goal": "Review energy and supplies.", "domains": ["energy", "inventory"]},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["domains"] == ["energy", "inventory"]
        assert [item["domain"] for item in result["recommendations"]] == ["energy", "inventory"]
        assert [step["node"] for step in result["trace"]] == [
            "supervisor",
            "energy_specialist",
            "inventory_specialist",
        ]

        persisted = client.get(f"/api/agents/runs/{result['id']}")
        assert persisted.status_code == 200
        assert persisted.json()["id"] == result["id"]


def test_agent_run_rejects_unknown_domain_and_missing_run():
    initialize_database()
    with TestClient(app) as client:
        response = client.post(
            "/api/agents/runs",
            json={"goal": "Review household.", "domains": ["unknown"]},
        )
        assert response.status_code == 422
        assert client.get("/api/agents/runs/not-a-real-run").status_code == 404
