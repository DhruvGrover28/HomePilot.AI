from fastapi.testclient import TestClient

from app.db import initialize_database
from app.main import app
from app.services.monitoring_runtime import monitoring_runtime


def test_health():
    initialize_database()
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_bad_csv_reports_row_errors():
    initialize_database()
    with TestClient(app) as client:
        response = client.post(
            "/api/readings/import",
            files={"file": ("readings.csv", b"type,reading_date,meter_value,consumption,period_days\nbad,not-a-date,,x,0\n", "text/csv")},
        )
    assert response.status_code == 422
    assert "row 2" in str(response.json())


def test_resource_crud_and_missing_resource_errors():
    initialize_database()
    with TestClient(app) as client:
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
    with TestClient(app) as client:
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
    with TestClient(app) as client:
        response = client.post(
            "/api/inventory",
            json={"name": "Rejected monitoring", "quantity": 1, "unit": "unit", "reorder_threshold": 2},
        )
    assert response.status_code == 200
