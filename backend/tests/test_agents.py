from fastapi.testclient import TestClient
import pytest

from app.config import get_settings
from app.db import initialize_database
from app.main import app
from app.services import agent_graph
from app.services.agent_graph import _recommendations, execute_agent


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_agent_run_routes_domains_and_persists_result(mock_mode):
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
        assert result["trace"][0]["kind"] == "decision"
        assert result["findings"]
        assert any(step["kind"] == "tool_call" for step in result["trace"])
        finding_ids = {finding["id"] for finding in result["findings"]}
        assert all(set(item["finding_ids"]) <= finding_ids for item in result["recommendations"])

        persisted = client.get(f"/api/agents/runs/{result['id']}")
        assert persisted.status_code == 200
        assert persisted.json()["id"] == result["id"]


def test_agent_run_rejects_unknown_domain_and_missing_run(mock_mode):
    initialize_database()
    with TestClient(app) as client:
        response = client.post(
            "/api/agents/runs",
            json={"goal": "Review household.", "domains": ["unknown"]},
        )
        assert response.status_code == 422
        assert client.get("/api/agents/runs/not-a-real-run").status_code == 404


def test_electricity_spike_can_trigger_maintenance_follow_up(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {
            "type": "energy_readings",
            "count": 6,
            "rates": [10, 10, 10, 10, 10, 25],
            "statistics": {"mean": 12.5, "standard_deviation": 5.59, "count": 6},
            "anomaly": {"flagged": True, "insufficient_data": False, "z_score": 2.2},
        },),
    )
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "maintenance",
        (lambda: {"type": "maintenance_statuses", "today": "2026-11-14", "items": []},),
    )
    result = execute_agent("Investigate an electricity spike.", ["energy", "maintenance"])
    assert [decision["specialist"] for decision in result["decisions"][:2]] == ["energy", "maintenance"]
    decisions = [entry for entry in result["trace"] if entry["kind"] == "decision"]
    assert decisions[0]["findings_seen"] == 0
    assert decisions[1]["findings_seen"] == 1
    assert result["recommendations"][0]["finding_ids"] == [result["findings"][0]["id"]]


def test_water_only_concern_does_not_invoke_unrelated_specialists(mock_mode, monkeypatch):
    calls = []

    def water_tool():
        calls.append("water")
        return {"type": "water_readings", "count": 6, "rates": [1, 1, 1, 1, 1, 1], "statistics": {}, "anomaly": {"flagged": False}}

    monkeypatch.setitem(agent_graph.TOOLSETS, "water", (water_tool,))
    monkeypatch.setitem(agent_graph.TOOLSETS, "energy", (lambda: calls.append("energy"),))
    result = execute_agent("Investigate water usage.", ["energy", "water", "maintenance"])
    assert calls == ["water"]
    assert [decision["specialist"] for decision in result["decisions"] if decision["action"] == "investigate"] == ["water"]


def test_inventory_and_insufficient_history_are_evidence_bounded(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "inventory",
        (lambda: {"type": "inventory_levels", "items": [{"item": "Milk", "quantity": 0, "unit": "unit", "reorder_threshold": 1, "low": True}]},),
    )
    inventory = execute_agent("Check low inventory.", ["inventory", "energy"])
    assert [decision["specialist"] for decision in inventory["decisions"] if decision["action"] == "investigate"] == ["inventory"]
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {"type": "energy_readings", "count": 2, "rates": [5, 6], "statistics": {}, "anomaly": {"insufficient_data": True}},),
    )
    insufficient = execute_agent("Investigate an electricity spike.", ["energy"])
    assert insufficient["findings"][0]["severity"] == "info"
    assert "Collect at least five" in insufficient["findings"][0]["suggested_action"]


def test_no_relevant_issue_and_budget_exhaustion_are_recorded(mock_mode):
    no_issue = execute_agent("Tell me something unrelated.", ["energy", "water"])
    assert no_issue["decisions"][0]["action"] == "stop"
    assert not [entry for entry in no_issue["trace"] if entry["kind"] == "tool_call"]
    exhausted = execute_agent("Investigate energy.", ["energy"], supervisor_budget=0)
    assert exhausted["stop_reason"] == "supervisor_budget_exhausted"
    assert exhausted["trace"][0]["kind"] == "budget_exhausted"


def test_specialist_budget_and_duplicate_suppression_are_enforced(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {"type": "energy_readings", "count": 6, "rates": [1, 1, 1, 1, 1, 4], "statistics": {}, "anomaly": {"flagged": True}},),
    )
    exhausted = execute_agent("Investigate energy.", ["energy"], specialist_budget=0)
    assert exhausted["status"] == "stopped"
    assert exhausted["stop_reason"] == "specialist_budget_exhausted"
    assert any(entry["kind"] == "budget_exhausted" for entry in exhausted["trace"])
    findings = [
        {
            "id": "a",
            "category": "energy",
            "subject": "electricity",
            "summary": "Spike",
            "evidence": [{"type": "energy_readings"}],
            "severity": "high",
            "confidence": 0.9,
            "possible_explanations": ["usage"],
            "suggested_action": "Review usage.",
        },
        {
            "id": "b",
            "category": "energy",
            "subject": "electricity",
            "summary": "Same spike",
            "evidence": [{"type": "energy_readings"}],
            "severity": "high",
            "confidence": 0.9,
            "possible_explanations": ["usage"],
            "suggested_action": "Review usage.",
        },
    ]
    recommendations, trace = _recommendations(findings)
    assert len(recommendations) == 2
    assert recommendations[1]["suppressed"] is True
    assert trace[0]["kind"] == "recommendation_suppressed"
