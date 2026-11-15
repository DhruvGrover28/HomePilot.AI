from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import initialize_database
from app.main import app

# Minimal 1x1 valid PNG bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal 1x1 valid JPEG bytes
TINY_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"


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
            "full_name": "Vision Tester",
            "email": f"{uuid4()}@example.com",
            "password": "correct horse battery",
            "confirm_password": "correct horse battery",
        },
    )
    return client


def test_inventory_scan_requires_auth():
    initialize_database()
    with TestClient(app) as client:
        res = client.post(
            "/api/inventory/scan",
            files={"file": ("shelf.png", TINY_PNG, "image/png")},
        )
        assert res.status_code == 401

        res2 = client.post(
            "/api/inventory/reconcile",
            json={"items": []},
        )
        assert res2.status_code == 401


def test_inventory_scan_rejects_unsupported_format(mock_mode):
    initialize_database()
    with _auth_client() as client:
        # Unsupported file extension
        res = client.post(
            "/api/inventory/scan",
            files={"file": ("shelf.txt", b"not an image", "text/plain")},
        )
        assert res.status_code == 400
        assert "Allowed formats" in res.json()["detail"]

        # Supported extension but corrupt magic bytes
        res2 = client.post(
            "/api/inventory/scan",
            files={"file": ("shelf.png", b"fake png content", "image/png")},
        )
        assert res2.status_code == 400
        assert "Corrupt or invalid" in res2.json()["detail"]


def test_inventory_scan_rejects_oversized_file(mock_mode):
    initialize_database()
    with _auth_client() as client:
        huge_bytes = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (11 * 1024 * 1024))
        res = client.post(
            "/api/inventory/scan",
            files={"file": ("huge.png", huge_bytes, "image/png")},
        )
        assert res.status_code == 400
        assert "exceeds" in res.json()["detail"]


def test_inventory_scan_and_prematch(mock_mode):
    initialize_database()
    with _auth_client() as client:
        # Pre-seed existing item "Whole Milk" with qty 2
        seeded = client.post(
            "/api/inventory",
            json={
                "name": "Whole Milk",
                "quantity": 2.0,
                "unit": "carton",
                "reorder_threshold": 1.0,
            },
        ).json()

        # Perform image scan
        res = client.post(
            "/api/inventory/scan",
            files={"file": ("pantry.png", TINY_PNG, "image/png")},
        )
        assert res.status_code == 200
        data = res.json()
        assert "detected_items" in data
        assert len(data["detected_items"]) > 0

        # Verify Whole Milk was matched against existing inventory
        milk = next((item for item in data["detected_items"] if "Milk" in item["name"]), None)
        assert milk is not None
        assert milk["matched_item_id"] == seeded["id"]
        assert milk["existing_quantity"] == 2.0
        assert milk["estimated_quantity"] == 3.0
        assert milk["confidence"] >= 0.8


def test_inventory_reconciliation_workflows(mock_mode):
    initialize_database()
    with _auth_client() as client:
        # Seed an item: Water Bottles (qty 10)
        item1 = client.post(
            "/api/inventory",
            json={
                "name": "Water Bottles",
                "quantity": 10.0,
                "unit": "bottle",
                "reorder_threshold": 3.0,
            },
        ).json()

        # Seed an item: Milk (qty 1)
        item2 = client.post(
            "/api/inventory",
            json={
                "name": "Whole Milk",
                "quantity": 1.0,
                "unit": "carton",
                "reorder_threshold": 2.0,
            },
        ).json()

        # Perform reconciliation:
        # 1. Add 5 to Milk (1 + 5 = 6)
        # 2. Replace Water Bottles count with 3 (verified count on shelf)
        # 3. Create a new item "Basmati Rice" (qty 2)
        # 4. Ignore an item
        reconcile_payload = {
            "items": [
                {
                    "action": "add",
                    "item_id": item2["id"],
                    "name": "Whole Milk",
                    "quantity": 5.0,
                    "unit": "carton",
                    "category": "beverage",
                    "reorder_threshold": 2.0,
                },
                {
                    "action": "replace",
                    "item_id": item1["id"],
                    "name": "Water Bottles",
                    "quantity": 3.0,
                    "unit": "bottle",
                    "category": "beverage",
                    "reorder_threshold": 3.0,
                },
                {
                    "action": "new",
                    "name": "Basmati Rice",
                    "quantity": 2.0,
                    "unit": "packet",
                    "category": "pantry",
                    "reorder_threshold": 1.0,
                },
                {
                    "action": "ignore",
                    "name": "Random Item",
                    "quantity": 1.0,
                    "unit": "box",
                    "category": "general",
                    "reorder_threshold": 1.0,
                },
            ]
        }

        rec_res = client.post("/api/inventory/reconcile", json=reconcile_payload)
        assert rec_res.status_code == 200
        rec_data = rec_res.json()
        assert len(rec_data["updated_items"]) == 2
        assert len(rec_data["created_items"]) == 1
        assert rec_data["ignored_count"] == 1

        # Verify database was updated correctly
        all_inv = {item["name"]: item["quantity"] for item in client.get("/api/inventory").json()}
        assert all_inv["Whole Milk"] == 6.0  # 1 + 5
        assert all_inv["Water Bottles"] == 3.0  # replaced to 3
        assert all_inv["Basmati Rice"] == 2.0  # newly created


def test_inventory_reconciliation_household_isolation(mock_mode):
    initialize_database()
    with _auth_client() as client_a, _auth_client() as client_b:
        # Client A creates item
        item_a = client_a.post(
            "/api/inventory",
            json={
                "name": "Household A Rice",
                "quantity": 5.0,
                "unit": "packet",
                "reorder_threshold": 1.0,
            },
        ).json()

        # Client B attempts to mutate Client A's item via reconciliation
        res = client_b.post(
            "/api/inventory/reconcile",
            json={
                "items": [
                    {
                        "action": "replace",
                        "item_id": item_a["id"],
                        "name": "Hacked Rice",
                        "quantity": 999.0,
                        "unit": "packet",
                        "category": "pantry",
                        "reorder_threshold": 1.0,
                    }
                ]
            },
        )
        assert res.status_code == 422
        assert "not found in this household" in res.json()["detail"]

        # Ensure Client A's quantity remains 5.0
        assert client_a.get("/api/inventory").json()[0]["quantity"] == 5.0
