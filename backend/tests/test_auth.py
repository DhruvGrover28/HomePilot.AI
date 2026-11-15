from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from app import clock

from app.db import initialize_database
from app.db.models import Household, User
from app.db.session import SessionLocal
from app.main import app


def test_register_login_me_and_logout():
    initialize_database()
    email = f"{uuid4()}@example.com"
    with TestClient(app) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test Owner",
                "email": email,
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        )
        assert registered.status_code == 201
        assert registered.json()["user"]["email"] == email
        assert "homepilot_session=" in registered.headers["set-cookie"]

        current = client.get("/api/auth/me")
        assert current.status_code == 200
        assert current.json()["full_name"] == "Test Owner"

        logged_out = client.post("/api/auth/logout")
        assert logged_out.status_code == 204
        assert client.get("/api/auth/me").status_code == 401

        logged_in = client.post(
            "/api/auth/login",
            json={"email": email, "password": "correct horse battery"},
        )
        assert logged_in.status_code == 200
        assert client.get("/api/auth/household").status_code == 200

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).one()
        assert user.password_hash.startswith("pbkdf2_sha256$")
        assert "correct horse battery" not in user.password_hash


def test_auth_rejects_duplicate_and_invalid_credentials():
    initialize_database()
    email = f"{uuid4()}@example.com"
    payload = {
        "full_name": "Duplicate Owner",
        "email": email,
        "password": "correct horse battery",
        "confirm_password": "correct horse battery",
    }
    with TestClient(app) as client:
        assert client.post("/api/auth/register", json=payload).status_code == 201
        assert client.post("/api/auth/register", json=payload).status_code == 409
        assert client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong password"},
        ).status_code == 401
        assert client.post(
            "/api/auth/register",
            json={**payload, "email": "not-an-email"},
        ).status_code == 422


def test_authenticated_households_cannot_access_each_others_readings():
    initialize_database()
    first = {
        "full_name": "First Owner",
        "email": f"{uuid4()}@example.com",
        "password": "correct horse battery",
        "confirm_password": "correct horse battery",
    }
    second = {
        "full_name": "Second Owner",
        "email": f"{uuid4()}@example.com",
        "password": "correct horse battery",
        "confirm_password": "correct horse battery",
    }
    with TestClient(app) as first_client, TestClient(app) as second_client:
        assert first_client.post("/api/auth/register", json=first).status_code == 201
        assert second_client.post("/api/auth/register", json=second).status_code == 201
        created = first_client.post(
            "/api/readings",
            json={
                "type": "electricity",
                "reading_date": date.today().isoformat(),
                "meter_value": 10,
                "consumption": 10,
                "period_days": 1,
                "unit": "kWh",
                "source": "manual",
            },
        )
        assert created.status_code == 200
        reading_id = created.json()["id"]

        assert [row["id"] for row in first_client.get("/api/readings").json()] == [reading_id]
        assert second_client.get("/api/readings").json() == []
        assert second_client.patch(
            f"/api/readings/{reading_id}",
            json={
                "type": "electricity",
                "reading_date": date.today().isoformat(),
                "meter_value": 11,
                "consumption": 11,
                "period_days": 1,
                "unit": "kWh",
                "source": "manual",
            },
        ).status_code == 404
        assert second_client.delete(f"/api/readings/{reading_id}").status_code == 404


def test_agent_investigations_and_tools_are_isolated_by_household(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    initialize_database()
    first = {
        "full_name": "Household One Owner",
        "email": f"{uuid4()}@example.com",
        "password": "correct horse battery",
        "confirm_password": "correct horse battery",
    }
    second = {
        "full_name": "Household Two Owner",
        "email": f"{uuid4()}@example.com",
        "password": "correct horse battery",
        "confirm_password": "correct horse battery",
    }
    with TestClient(app) as first_client, TestClient(app) as second_client:
        assert first_client.post("/api/auth/register", json=first).status_code == 201
        assert second_client.post("/api/auth/register", json=second).status_code == 201

        # Household 1 creates an appliance and spike readings
        appliance_a = first_client.post(
            "/api/appliances",
            json={"name": "Household A Heat Pump", "category": "heating"},
        ).json()
        assert appliance_a["name"] == "Household A Heat Pump"

        for index, val in enumerate([10.0, 10.0, 10.0, 10.0, 10.0, 30.0]):
            first_client.post(
                "/api/readings",
                json={
                    "type": "electricity",
                    "reading_date": f"2026-01-0{index + 1}",
                    "meter_value": 100.0 + (index * 10.0),
                    "consumption": val,
                    "period_days": 1,
                    "unit": "kWh",
                    "source": "manual",
                },
            )

        # Household 2 creates an appliance
        appliance_b = second_client.post(
            "/api/appliances",
            json={"name": "Household B Dishwasher", "category": "kitchen"},
        ).json()
        assert appliance_b["name"] == "Household B Dishwasher"

        # Household 1 runs agent analysis
        run_res_1 = first_client.post(
            "/api/agents/runs",
            json={"goal": "Investigate electricity spike and appliances.", "domains": ["energy", "maintenance"]},
        )
        assert run_res_1.status_code == 200
        run_1 = run_res_1.json()

        # Household 2 cannot view Household 1's agent run
        assert second_client.get(f"/api/agents/runs/{run_1['id']}").status_code == 404

        # Verify findings in Household 1's run only inspect Household 1's appliance
        maintenance_tool_calls = [
            step["result"] for step in run_1["trace"]
            if step.get("kind") == "tool_call" and step.get("tool") == "maintenance_statuses"
        ]
        assert len(maintenance_tool_calls) > 0
        items_evaluated = maintenance_tool_calls[0]["items"]
        appliance_names = [item["appliance"] for item in items_evaluated]
        assert "Household A Heat Pump" in appliance_names
        assert "Household B Dishwasher" not in appliance_names

        # Household 2 runs agent analysis
        run_res_2 = second_client.post(
            "/api/agents/runs",
            json={"goal": "Review appliances.", "domains": ["maintenance"]},
        )
        assert run_res_2.status_code == 200
        run_2 = run_res_2.json()

        assert first_client.get(f"/api/agents/runs/{run_2['id']}").status_code == 404
        maintenance_tool_calls_2 = [
            step["result"] for step in run_2["trace"]
            if step.get("kind") == "tool_call" and step.get("tool") == "maintenance_statuses"
        ]
        assert len(maintenance_tool_calls_2) > 0
        items_evaluated_2 = maintenance_tool_calls_2[0]["items"]
        appliance_names_2 = [item["appliance"] for item in items_evaluated_2]
        assert "Household B Dishwasher" in appliance_names_2
        assert "Household A Heat Pump" not in appliance_names_2


def test_profile_and_household_settings_update():
    initialize_database()
    email = f"{uuid4()}@example.com"
    with TestClient(app) as client:
        client.post(
            "/api/auth/register",
            json={
                "full_name": "Original Name",
                "email": email,
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        )
        # Update profile
        patched_user = client.patch(
            "/api/auth/me",
            json={"full_name": "Updated Name", "theme_preference": "dark"},
        )
        assert patched_user.status_code == 200
        assert patched_user.json()["full_name"] == "Updated Name"
        assert patched_user.json()["theme_preference"] == "dark"

        # Change password
        bad_change = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "wrong password",
                "new_password": "new password 123",
                "confirm_password": "new password 123",
            },
        )
        assert bad_change.status_code == 400

        good_change = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "correct horse battery",
                "new_password": "new password 123",
                "confirm_password": "new password 123",
            },
        )
        assert good_change.status_code == 200

        # Update household settings & onboarding
        patched_hh = client.patch(
            "/api/auth/household",
            json={
                "name": "Green Villa",
                "timezone": "America/New_York",
                "preferred_units": "imperial",
                "onboarding_completed": True,
            },
        )
        assert patched_hh.status_code == 200
        hh_data = patched_hh.json()
        assert hh_data["name"] == "Green Villa"
        assert hh_data["timezone"] == "America/New_York"
        assert hh_data["preferred_units"] == "imperial"
        assert hh_data["onboarding_completed"] is True


def test_assistant_chat_and_history(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    initialize_database()
    email = f"{uuid4()}@example.com"
    with TestClient(app) as client:
        client.post(
            "/api/auth/register",
            json={
                "full_name": "Assistant Tester",
                "email": email,
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        )
        # Add an appliance
        client.post("/api/appliances", json={"name": "Smart Washer", "category": "laundry"})

        # Chat with assistant
        res = client.post("/api/assistant/chat", json={"message": "Are any appliances due for maintenance?"})
        assert res.status_code == 200
        chat_data = res.json()
        assert "Smart Washer" in chat_data["reply"] or "appliances" in chat_data["reply"]
        assert len(chat_data["suggested_prompts"]) > 0

        # Check history
        history_res = client.get("/api/assistant/history")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

        # Ask to investigate
        inv_res = client.post("/api/assistant/chat", json={"message": "Investigate electricity and appliances."})
        assert inv_res.status_code == 200
        inv_data = inv_res.json()
        assert inv_data["agent_run"] is not None
        assert inv_data["agent_run"]["status"] == "completed"

        # Clear history
        del_res = client.delete("/api/assistant/history")
        assert del_res.status_code == 204
        assert len(client.get("/api/assistant/history").json()) == 0


def test_comprehensive_two_household_isolation_and_unowned_fail_closed(monkeypatch):
    from app.config import get_settings
    from app.db.models import Reading, Appliance, InventoryItem
    from app.services.agent_tools import (
        energy_readings,
        water_readings,
        maintenance_statuses,
        inventory_levels,
    )
    from app.services.monitoring_runtime import monitoring_runtime
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    initialize_database()

    # 1. Insert unowned legacy records with household_id = None
    with SessionLocal() as session:
        session.add(
            Reading(
                type="electricity",
                reading_date=date(2025, 1, 1),
                meter_value=100.0,
                consumption=25.0,
                period_days=1,
                unit="kWh",
                source="manual",
                household_id=None,
                created_at=clock.now(),
            )
        )
        session.add(
            Appliance(
                name="Legacy Unowned Furnace",
                category="heating",
                household_id=None,
                created_at=clock.now(),
            )
        )
        session.commit()

    # 2. Verify that missing context fails closed (returns 0 records, never legacy unowned records)
    assert energy_readings(household_id=None)["count"] == 0
    assert energy_readings(household_id=None)["rates"] == []
    assert water_readings(household_id=None)["count"] == 0
    assert maintenance_statuses(household_id=None)["items"] == []
    assert inventory_levels(household_id=None)["items"] == []

    # 3. Register two isolated households
    h1_email = f"{uuid4()}@example.com"
    h2_email = f"{uuid4()}@example.com"
    with TestClient(app) as h1_client, TestClient(app) as h2_client:
        h1_auth = h1_client.post(
            "/api/auth/register",
            json={
                "full_name": "Household One",
                "email": h1_email,
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        ).json()
        h2_auth = h2_client.post(
            "/api/auth/register",
            json={
                "full_name": "Household Two",
                "email": h2_email,
                "password": "correct horse battery",
                "confirm_password": "correct horse battery",
            },
        ).json()
        h1_id = h1_auth["household_id"]
        h2_id = h2_auth["household_id"]

        # Household 1 creates electricity readings and appliance
        for i in range(5):
            h1_client.post(
                "/api/readings",
                json={
                    "type": "electricity",
                    "reading_date": f"2026-02-0{i+1}",
                    "meter_value": 10.0 * (i + 1),
                    "consumption": 10.0,
                    "period_days": 1,
                    "unit": "kWh",
                    "source": "manual",
                },
            )
        h1_client.post("/api/appliances", json={"name": "H1 Solar Inverter", "category": "energy"})

        # Household 2 creates water readings and inventory
        for i in range(5):
            h2_client.post(
                "/api/readings",
                json={
                    "type": "water",
                    "reading_date": f"2026-02-0{i+1}",
                    "meter_value": 100.0 * (i + 1),
                    "consumption": 100.0,
                    "period_days": 1,
                    "unit": "litres",
                    "source": "manual",
                },
            )
        h2_client.post(
            "/api/inventory",
            json={"name": "H2 Water Filters", "category": "water", "quantity": 1, "unit": "pack", "reorder_threshold": 2},
        )

        # 4. Direct tool verification: strict isolation between households
        h1_energy = energy_readings(h1_id)
        h2_energy = energy_readings(h2_id)
        assert h1_energy["count"] == 5
        assert h2_energy["count"] == 0

        h1_water = water_readings(h1_id)
        h2_water = water_readings(h2_id)
        assert h1_water["count"] == 0
        assert h2_water["count"] == 5

        h1_maint = maintenance_statuses(h1_id)
        h2_maint = maintenance_statuses(h2_id)
        assert len(h1_maint["items"]) == 1
        assert h1_maint["items"][0]["appliance"] == "H1 Solar Inverter"
        assert len(h2_maint["items"]) == 0

        h1_inv = inventory_levels(h1_id)
        h2_inv = inventory_levels(h2_id)
        assert len(h1_inv["items"]) == 0
        assert len(h2_inv["items"]) == 1
        assert h2_inv["items"][0]["item"] == "H2 Water Filters"

        # 5. Assistant conversation isolation
        h1_client.post("/api/assistant/chat", json={"message": "What is my solar status?"})
        h2_client.post("/api/assistant/chat", json={"message": "How many water filters do I have?"})

        h1_history = h1_client.get("/api/assistant/history").json()
        h2_history = h2_client.get("/api/assistant/history").json()
        assert len(h1_history) == 2
        assert any("solar status" in m["content"] for m in h1_history)
        assert not any("water filters" in m["content"] for m in h1_history)

        assert len(h2_history) == 2
        assert any("water filters" in m["content"] for m in h2_history)
        assert not any("solar status" in m["content"] for m in h2_history)

        # Clear H1 history; H2 history remains intact
        assert h1_client.delete("/api/assistant/history").status_code == 204
        assert len(h1_client.get("/api/assistant/history").json()) == 0
        assert len(h2_client.get("/api/assistant/history").json()) == 2

        # 6. Background execution / scheduled check isolation
        monitoring_runtime.run_scheduled_check()
        h1_issues = h1_client.get("/api/monitoring/issues").json()
        h2_issues = h2_client.get("/api/monitoring/issues").json()
        for issue in h1_issues:
            assert issue["domain"] != "inventory"
        for issue in h2_issues:
            assert issue["domain"] != "energy"

        # 7. Account deletion
        del_user = h1_client.delete("/api/auth/me")
        assert del_user.status_code == 204
        assert h1_client.get("/api/auth/me").status_code == 401
        assert h2_client.get("/api/auth/me").status_code == 200


def test_sqlite_foreign_keys_are_enforced():
    """Verify that foreign key constraints are strictly enforced in SQLite."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    initialize_database()
    with SessionLocal() as session:
        orphan_household = Household(
            id=str(uuid4()),
            name="Orphan Household",
            owner_id="non-existent-user-id",
            created_at=clock.now(),
        )
        session.add(orphan_household)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_registration_persists_user_before_household_and_sets_correct_owner():
    """Verify registration creates user first, links household, and sets owner_id."""
    initialize_database()
    email = f"order_{uuid4()}@example.com"
    payload = {
        "full_name": "Sequenced User",
        "email": email,
        "password": "valid_secure_pass123",
        "confirm_password": "valid_secure_pass123",
    }
    with TestClient(app) as client:
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        user_id = data["user"]["id"]
        household_id = data["household_id"]

    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user is not None
        assert user.email == email
        assert user.full_name == "Sequenced User"

        household = session.get(Household, household_id)
        assert household is not None
        assert household.owner_id == user.id


def test_registration_atomic_rollback_on_failure(monkeypatch):
    """Verify atomicity: if an error occurs during registration, user and household are rolled back."""
    import app.services.auth as auth_service

    initialize_database()
    email = f"fail_{uuid4()}@example.com"
    payload = {
        "full_name": "Rollback Test User",
        "email": email,
        "password": "valid_secure_pass123",
        "confirm_password": "valid_secure_pass123",
    }

    # Simulate failure right after household is added/flushed
    def fail_create_session(session, user_id, response):
        raise RuntimeError("Simulated transaction failure")

    monkeypatch.setattr(auth_service, "_create_session", fail_create_session)

    with TestClient(app) as client:
        import pytest
        with pytest.raises(RuntimeError, match="Simulated transaction failure"):
            client.post("/api/auth/register", json=payload)

    # Verify atomic rollback left no orphaned user in the database
    with SessionLocal() as session:
        persisted_user = session.query(User).filter(User.email == email).first()
        assert persisted_user is None


def test_registration_password_mismatch_returns_422():
    initialize_database()
    payload = {
        "full_name": "Mismatch User",
        "email": f"mismatch_{uuid4()}@example.com",
        "password": "valid_secure_pass123",
        "confirm_password": "different_pass123",
    }
    with TestClient(app) as client:
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 422
        assert "Passwords do not match" in res.text


def test_registration_preserves_passwords_with_exact_whitespace():
    """Ensure intentional leading/trailing spaces in passwords are kept exactly."""
    initialize_database()
    email = f"spaces_{uuid4()}@example.com"
    spaced_pass = "   spaced passphrase 123   "
    payload = {
        "full_name": "Spaced Password User",
        "email": email,
        "password": spaced_pass,
        "confirm_password": spaced_pass,
    }
    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json=payload)
        assert registered.status_code == 201

        # Login with exact spaced password must succeed
        login_exact = client.post("/api/auth/login", json={"email": email, "password": spaced_pass})
        assert login_exact.status_code == 200

        # Login with stripped password must fail (spaces were preserved, not stripped)
        login_stripped = client.post(
            "/api/auth/login",
            json={"email": email, "password": spaced_pass.strip()},
        )
        assert login_stripped.status_code == 401


def test_registration_normalizes_full_name_and_email():
    """Verify full_name and email are safely trimmed/lowercased, and blank full_name is rejected."""
    initialize_database()
    raw_email = f"  Trimmed_{uuid4()}@Example.COM  "
    expected_email = raw_email.strip().lower()
    payload = {
        "full_name": "  Trimmed User  ",
        "email": raw_email,
        "password": "valid_secure_pass123",
        "confirm_password": "valid_secure_pass123",
    }
    with TestClient(app) as client:
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 201
        assert res.json()["user"]["full_name"] == "Trimmed User"
        assert res.json()["user"]["email"] == expected_email

        # Blank/whitespace-only full_name must be rejected with 422
        blank_name_payload = {
            "full_name": "    ",
            "email": f"blank_{uuid4()}@example.com",
            "password": "valid_secure_pass123",
            "confirm_password": "valid_secure_pass123",
        }
        res_blank = client.post("/api/auth/register", json=blank_name_payload)
        assert res_blank.status_code == 422
