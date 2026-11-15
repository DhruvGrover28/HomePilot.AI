from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.schemas_monitoring import MonitoringIssueOut
from app.services import household_intelligence
from app.services.household_intelligence import build_household_intelligence


def _issue(issue_id: str, domain: str, *, entity_id: int | None = None) -> MonitoringIssueOut:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return MonitoringIssueOut(
        id=issue_id,
        fingerprint=f"{domain}:{issue_id}",
        issue_type="consumption_anomaly" if domain == "energy" else "maintenance_due",
        domain=domain,
        entity_id=entity_id,
        title=f"{domain} issue",
        issue_status="open",
        first_trigger_source="manual",
        last_trigger_source="manual",
        first_detected_at=now,
        last_detected_at=now,
        resolved_at=None,
        occurrence_count=1,
        latest_evidence_id=None,
        details=(
            {"anomaly": {"flagged": True, "percent_change": 60}}
            if domain == "energy"
            else {"maintenance": {"status": "overdue"}}
        ),
        investigation_id=None,
        investigation_status="completed",
        active_run_id=None,
        latest_run_id="run-1" if issue_id == "energy-issue" else None,
        claimed_at=None,
        started_at=None,
        completed_at=None,
        last_error=None,
    )


def test_empty_household_intelligence_is_valid(monkeypatch):
    monkeypatch.setattr(household_intelligence, "list_monitoring_issues", lambda issue_status=None: [])
    assert build_household_intelligence() == {
        "open_issues": [],
        "relationships": [],
        "findings": [],
        "recommendations": [],
        "investigation_statuses": {},
        "warnings": [],
    }


def test_household_intelligence_aggregates_deterministic_relationships(monkeypatch):
    issues = [_issue("energy-issue", "energy"), _issue("maintenance-issue", "maintenance")]
    monkeypatch.setattr(
        household_intelligence,
        "list_monitoring_issues",
        lambda issue_status=None: issues,
    )
    monkeypatch.setattr(
        household_intelligence,
        "get_agent_run",
        lambda run_id: {
            "id": "run-1",
            "status": "completed",
            "findings": [
                {
                    "id": "finding-1",
                    "severity": "high",
                    "confidence": 0.9,
                    "evidence": [{"reading_id": 1}],
                    "summary": "Energy spike",
                }
            ],
            "recommendations": [
                {
                    "finding_ids": ["finding-1"],
                    "suggested_action": "Review the latest reading.",
                    "summary": "Review usage.",
                }
            ],
        },
    )

    result = build_household_intelligence()

    assert len(result["open_issues"]) == 2
    assert result["relationships"][0]["relationship"] == "plausible"
    assert result["findings"][0]["issue_id"] == "energy-issue"
    assert result["recommendations"][0]["issue_id"] == "energy-issue"


def test_intelligence_summary_route_returns_service_payload(monkeypatch):
    from uuid import uuid4
    from app.db import initialize_database
    initialize_database()
    payload = {
        "open_issues": [],
        "relationships": [],
        "findings": [],
        "recommendations": [],
        "investigation_statuses": {},
        "warnings": [],
    }
    monkeypatch.setattr(
        "app.routers.intelligence.build_household_intelligence",
        lambda household_id: payload,
    )
    with TestClient(app) as client:
        client.post(
            "/api/auth/register",
            json={
                "full_name": "Intel Tester",
                "email": f"{uuid4()}@example.com",
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        )
        response = client.get("/api/intelligence/summary")
    assert response.status_code == 200
    assert response.json() == payload
