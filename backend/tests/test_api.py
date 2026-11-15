from uuid import uuid4
from fastapi.testclient import TestClient

from app.db import initialize_database
from app.main import app
from app.services.monitoring_runtime import monitoring_runtime


def _auth_client() -> TestClient:
    client = TestClient(app)
    client.post(
        "/api/auth/register",
        json={
            "full_name": "API Tester",
            "email": f"{uuid4()}@example.com",
            "password": "correct horse battery",
            "confirm_password": "correct horse battery",
        },
    )
    return client


def test_health():
    initialize_database()
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_sensitive_endpoints_reject_unauthenticated_requests():
    initialize_database()
    with TestClient(app) as client:
        assert client.get("/api/readings").status_code == 401
        assert client.get("/api/appliances").status_code == 401
        assert client.get("/api/inventory").status_code == 401
        assert client.get("/api/shopping-list").status_code == 401
        assert client.get("/api/tasks").status_code == 401
        assert client.get("/api/dashboard/summary").status_code == 401
        assert client.get("/api/monitoring/issues").status_code == 401
        assert client.post("/api/monitoring/check", json={}).status_code == 401
        assert client.post("/api/agents/runs", json={"goal": "test"}).status_code == 401
        assert client.get("/api/agents/runs").status_code == 401
        assert client.get("/api/intelligence/summary").status_code == 401


def test_bad_csv_reports_row_errors():
    initialize_database()
    with _auth_client() as client:
        response = client.post(
            "/api/readings/import",
            files={"file": ("readings.csv", b"type,reading_date,meter_value,consumption,period_days\nbad,not-a-date,,x,0\n", "text/csv")},
        )
    assert response.status_code == 422
    assert "row 2" in str(response.json())


def test_resource_crud_and_missing_resource_errors():
    initialize_database()
    with _auth_client() as client:
        appliance = client.post("/api/appliances", json={"name": "Test appliance", "category": "test"}).json()
        updated = client.patch(
            f"/api/appliances/{appliance['id']}",
            json={"name": "Updated appliance", "category": "test"},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated appliance"
        assert client.delete(f"/api/appliances/{appliance['id']}").status_code == 204
        assert client.delete(f"/api/appliances/{appliance['id']}").status_code == 404

        item = client.post(
            "/api/inventory",
            json={"name": "Test item", "quantity": 2, "unit": "unit", "reorder_threshold": 1},
        ).json()
        assert client.delete(f"/api/inventory/{item['id']}").status_code == 204

        shopping = client.post(
            "/api/shopping-list", json={"item_name": "Test item", "quantity": 1, "unit": "unit"}
        ).json()
        assert client.patch(
            f"/api/shopping-list/{shopping['id']}",
            json={"item_name": "Updated item", "quantity": 2, "unit": "unit"},
        ).status_code == 200
        assert client.delete(f"/api/shopping-list/{shopping['id']}").status_code == 204

        task = client.post(
            "/api/tasks", json={"title": "Test task", "description": "", "due_date": "2026-12-01"}
        ).json()
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 204


def test_monitoring_api_uses_manual_shared_check_path():
    initialize_database()
    with _auth_client() as client:
        response = client.post("/api/monitoring/check", json={"domains": ["inventory"]})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert client.get("/api/monitoring/issues").status_code == 200
        assert client.post("/api/monitoring/check", json={"domains": ["unknown"]}).status_code == 422


def test_executor_rejection_does_not_fail_successful_inventory_mutation(monkeypatch):
    initialize_database()
    from app.services.monitoring_executor import MonitoringExecutor

    rejected_executor = MonitoringExecutor()
    monkeypatch.setattr(monitoring_runtime, "_executor", rejected_executor)
    with _auth_client() as client:
        response = client.post(
            "/api/inventory",
            json={"name": "Rejected monitoring", "quantity": 1, "unit": "unit", "reorder_threshold": 2},
        )
    assert response.status_code == 200


def test_end_to_end_saas_lifecycle_integration(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    initialize_database()

    with TestClient(app) as client:
        # 1. Health checks
        assert client.get("/health").status_code == 200
        assert client.get("/api/health").status_code == 200

        # 2. Unauthenticated check fails
        assert client.get("/api/dashboard/summary").status_code == 401

        # 3. Registration
        email = f"saas_{uuid4()}@example.com"
        reg = client.post(
            "/api/auth/register",
            json={
                "full_name": "SaaS Household Admin",
                "email": email,
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        )
        assert reg.status_code == 201
        household_id = reg.json()["household_id"]

        # 4. Check initial onboarding status (incomplete)
        hh = client.get("/api/auth/household").json()
        assert hh["onboarding_completed"] is False

        # 5. Update profile and theme
        prof = client.patch("/api/auth/me", json={"theme_preference": "dark"})
        assert prof.status_code == 200
        assert prof.json()["theme_preference"] == "dark"

        # 6. Complete onboarding wizard
        comp = client.patch(
            "/api/auth/household",
            json={
                "name": "Integrated Residence",
                "timezone": "America/New_York",
                "preferred_units": "imperial",
                "onboarding_completed": True,
            },
        )
        assert comp.status_code == 200
        assert comp.json()["onboarding_completed"] is True
        assert comp.json()["name"] == "Integrated Residence"

        # 7. Seed simulated demonstration telemetry
        seed_res = client.post("/api/demo/seed")
        assert seed_res.status_code == 200

        # 8. Dashboard summary
        summary_res = client.get("/api/dashboard/summary")
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert len(summary["electricity"]) > 0
        assert len(summary["water"]) > 0
        assert len(summary["appliances"]) > 0

        # 9. Run monitoring check
        mon_res = client.post("/api/monitoring/check", json={})
        assert mon_res.status_code == 200
        issues = mon_res.json()
        assert isinstance(issues, list)

        # 10. Agent investigation run
        run_res = client.post(
            "/api/agents/runs",
            json={"goal": "Audit household consumption and appliances.", "domains": ["energy", "maintenance"]},
        )
        assert run_res.status_code == 200
        run = run_res.json()
        assert run["status"] == "completed"
        assert len(run["findings"]) > 0
        assert len(run["recommendations"]) > 0

        # 11. Intelligence summary
        intel_res = client.get("/api/intelligence/summary")
        assert intel_res.status_code == 200
        intel = intel_res.json()
        assert "open_issues" in intel
        assert "recommendations" in intel

        # 12. Conversational Assistant
        chat_res = client.post(
            "/api/assistant/chat",
            json={"message": "What is our current electricity status?"},
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "reply" in chat_data
        assert len(chat_data["reply"]) > 10

        # 13. Assistant conversation history
        hist_res = client.get("/api/assistant/history")
        assert hist_res.status_code == 200
        assert len(hist_res.json()) >= 2

        # 14. Logout
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 204

        # 15. Verify unauthenticated access is blocked
        assert client.get("/api/dashboard/summary").status_code == 401
