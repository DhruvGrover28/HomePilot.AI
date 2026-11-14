from fastapi.testclient import TestClient

from app.db import initialize_database
from app.main import app


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
