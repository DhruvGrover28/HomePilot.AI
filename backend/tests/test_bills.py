import io
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import initialize_database
from app.main import app

# Minimal valid PDF bytes
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 21 >>\nstream\nBT /F1 12 Tf (Hello Bill) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n275\n%%EOF"

# Minimal valid PNG bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _auth_client() -> TestClient:
    client = TestClient(app)
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Bill Tester",
            "email": f"{uuid4()}@example.com",
            "password": "correct horse battery",
            "confirm_password": "correct horse battery",
        },
    )
    return client


def test_bill_endpoints_require_auth():
    initialize_database()
    with TestClient(app) as client:
        assert client.get("/api/bills").status_code == 401
        assert client.get("/api/bills/analysis?utility_type=electricity").status_code == 401
        assert client.get("/api/bills/some-id").status_code == 401
        assert client.get("/api/bills/some-id/csv").status_code == 401
        assert client.post("/api/bills/extract").status_code == 401
        assert client.post("/api/bills/confirm", json={}).status_code == 401


def test_bill_extract_validates_file_and_type(mock_mode):
    initialize_database()
    with _auth_client() as client:
        # Invalid utility_type
        res = client.post(
            "/api/bills/extract",
            data={"utility_type": "gas"},
            files={"file": ("bill.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert res.status_code == 422

        # Unsupported file extension
        res2 = client.post(
            "/api/bills/extract",
            data={"utility_type": "electricity"},
            files={"file": ("bill.txt", b"plain text", "text/plain")},
        )
        assert res2.status_code == 400
        assert "Allowed formats" in res2.json()["detail"]

        # Corrupt PDF header
        res3 = client.post(
            "/api/bills/extract",
            data={"utility_type": "electricity"},
            files={"file": ("bill.pdf", b"not a pdf", "application/pdf")},
        )
        assert res3.status_code == 400
        assert "Corrupt or invalid PDF" in res3.json()["detail"]


def test_bill_extract_and_confirm_lifecycle(mock_mode):
    initialize_database()
    with _auth_client() as client:
        # 1. Extract electricity bill from PDF
        res = client.post(
            "/api/bills/extract",
            data={"utility_type": "electricity"},
            files={"file": ("electric_bill.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert res.status_code == 200
        extracted = res.json()
        assert extracted["utility_type"] == "electricity"
        assert extracted["consumption_unit"] == "kWh"
        assert extracted["consumption"] > 0
        assert extracted["total_amount"] is not None

        # 2. Confirm and persist the extracted bill
        confirm_payload = {
            "utility_type": "electricity",
            "provider_name": extracted["provider_name"],
            "account_number": extracted["account_number"],
            "bill_number": extracted["bill_number"],
            "bill_date": extracted["bill_date"],
            "due_date": extracted["due_date"],
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
            "period_days": 30,
            "previous_reading": 1000.0,
            "current_reading": 1400.0,
            "consumption": 400.0,
            "consumption_unit": "kWh",
            "total_amount": 88.0,
            "currency": "USD",
            "fixed_charges": 15.0,
            "variable_charges": 68.0,
            "taxes": 5.0,
            "other_charges": 0.0,
            "source_filename": "electric_bill.pdf",
            "sync_reading": True,
        }

        save_res = client.post("/api/bills/confirm", json=confirm_payload)
        assert save_res.status_code == 200
        bill_data = save_res.json()
        assert bill_data["id"]
        assert bill_data["consumption"] == 400.0

        # Verify bill list
        bills_list = client.get("/api/bills?utility_type=electricity").json()
        assert len(bills_list) == 1
        assert bills_list[0]["id"] == bill_data["id"]

        # Verify CSV download
        csv_res = client.get(f"/api/bills/{bill_data['id']}/csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert "attachment" in csv_res.headers["content-disposition"]
        csv_text = csv_res.text
        assert "bill_id,household_id,utility_type" in csv_text
        assert "400.0" in csv_text
        assert "electricity" in csv_text

        # Verify synchronized Reading record
        readings = client.get("/api/readings?type=electricity").json()
        bill_reading = next((r for r in readings if r["source"] == "bill"), None)
        assert bill_reading is not None
        assert bill_reading["consumption"] == 400.0
        assert bill_reading["unit"] == "kWh"


def test_bill_deduplication(mock_mode):
    initialize_database()
    with _auth_client() as client:
        payload = {
            "utility_type": "water",
            "provider_name": "City Water",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
            "period_days": 31,
            "consumption": 15000.0,
            "consumption_unit": "litres",
            "total_amount": 45.0,
            "currency": "USD",
            "source_filename": "water_aug.pdf",
            "sync_reading": False,
        }

        res1 = client.post("/api/bills/confirm", json=payload)
        assert res1.status_code == 200

        # Attempt to import duplicate billing period
        res2 = client.post("/api/bills/confirm", json=payload)
        assert res2.status_code == 422
        assert "already been imported" in res2.json()["detail"]


def test_bill_household_isolation(mock_mode):
    initialize_database()
    with _auth_client() as client_a, _auth_client() as client_b:
        # Client A imports bill
        payload = {
            "utility_type": "electricity",
            "provider_name": "Private Grid A",
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "period_days": 31,
            "consumption": 350.0,
            "consumption_unit": "kWh",
            "total_amount": 70.0,
            "source_filename": "bill_a.pdf",
            "sync_reading": False,
        }
        bill_a = client_a.post("/api/bills/confirm", json=payload).json()
        bill_id = bill_a["id"]

        # Client B cannot view or download Client A's bill
        assert client_b.get("/api/bills").json() == []
        assert client_b.get(f"/api/bills/{bill_id}").status_code == 404
        assert client_b.get(f"/api/bills/{bill_id}/csv").status_code == 404


def test_bill_analysis_one_bill_versus_multiple(mock_mode):
    initialize_database()
    with _auth_client() as client:
        # Initially empty analysis
        empty_analysis = client.get("/api/bills/analysis?utility_type=electricity").json()
        assert empty_analysis["total_bills"] == 0
        assert empty_analysis["warnings"]

        # Add 1st bill: August
        client.post(
            "/api/bills/confirm",
            json={
                "utility_type": "electricity",
                "period_start": "2026-08-01",
                "period_end": "2026-08-31",
                "period_days": 31,
                "consumption": 310.0,  # 10 kWh/day
                "consumption_unit": "kWh",
                "total_amount": 62.0,
                "currency": "USD",
                "source_filename": "aug.pdf",
                "sync_reading": False,
            },
        )

        analysis_1 = client.get("/api/bills/analysis?utility_type=electricity").json()
        assert analysis_1["total_bills"] == 1
        assert analysis_1["average_consumption"] == 310.0
        assert analysis_1["consumption_trend_pct"] is None  # Cannot compute trend from 1 bill!
        assert any("cannot establish historical consumption trends" in w for w in analysis_1["warnings"])

        # Add 2nd bill: September (higher usage: 465 kWh = 15.5 kWh/day, +55%)
        client.post(
            "/api/bills/confirm",
            json={
                "utility_type": "electricity",
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "period_days": 30,
                "consumption": 465.0,  # 15.5 kWh/day
                "consumption_unit": "kWh",
                "total_amount": 93.0,
                "currency": "USD",
                "source_filename": "sep.pdf",
                "sync_reading": False,
            },
        )

        analysis_2 = client.get("/api/bills/analysis?utility_type=electricity").json()
        assert analysis_2["total_bills"] == 2
        assert analysis_2["consumption_trend_pct"] == 55.0  # (15.5 - 10) / 10 = +55%
        assert analysis_2["total_spend"] == 155.0  # 62 + 93
        assert analysis_2["cost_per_unit"] == 0.2  # 155 / 775 = 0.2 $/kWh
