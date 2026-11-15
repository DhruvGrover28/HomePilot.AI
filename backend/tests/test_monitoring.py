from datetime import date, timedelta
from threading import Event
from uuid import uuid4

from app import clock
from app.db import initialize_database
from app.db.models import Appliance, InventoryItem, MonitoringIssue, Reading
from app.db.session import SessionLocal
from app.services import monitoring as monitoring_service
from app.services.monitoring import evaluate_monitoring, get_monitoring_issue
from app.services.monitoring import monitor_and_investigate, queue_issue_investigation
from app.services import monitoring_executor as monitoring_executor_service
from app.services.monitoring_executor import MonitoringExecutor
from app.services.monitoring_runtime import MonitoringRuntime


def _add_readings(kind: str, values: list[float]) -> None:
    with SessionLocal() as session:
        for index, value in enumerate(values):
            session.add(
                Reading(
                    type=kind,
                    reading_date=date(2026, 1, 1) + timedelta(days=index),
                    meter_value=value,
                    period_days=1,
                    consumption=value,
                    unit="kWh" if kind == "electricity" else "litres",
                    source="manual",
                    created_at=clock.now(),
                )
            )
        session.commit()


def test_energy_uses_stable_domain_fingerprint_and_latest_evidence():
    initialize_database()
    _add_readings("electricity", [1, 1, 1, 1, 4])

    first = next(
        issue for issue in evaluate_monitoring("scheduled", ["energy"])
        if issue.fingerprint == "energy:anomaly"
    )
    first_evidence = first.latest_evidence_id

    _add_readings("electricity", [1, 1, 1, 1, 4, 5])
    second = next(
        issue for issue in evaluate_monitoring("event", ["energy"])
        if issue.fingerprint == "energy:anomaly"
    )
    assert second.latest_evidence_id != first_evidence
    assert second.first_trigger_source == "scheduled"
    assert second.last_trigger_source == "event"
    assert second.occurrence_count == first.occurrence_count + 1


def test_appliance_and_inventory_fingerprints_are_entity_specific():
    initialize_database()
    with SessionLocal() as session:
        washer = Appliance(
            name="Washer",
            category="laundry",
            last_service_date=date(2024, 1, 1),
            service_interval_days=30,
            created_at=clock.now(),
        )
        dryer = Appliance(
            name="Dryer",
            category="laundry",
            last_service_date=date(2024, 1, 1),
            service_interval_days=30,
            created_at=clock.now(),
        )
        soap = InventoryItem(
            name="Soap",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        rice = InventoryItem(
            name="Rice",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        session.add_all([washer, dryer, soap, rice])
        session.commit()
        appliance_ids = [washer.id, dryer.id]
        inventory_ids = [soap.id, rice.id]

    issues = evaluate_monitoring("manual", ["maintenance", "inventory"])
    fingerprints = {issue.fingerprint for issue in issues}
    assert {f"appliance:{item_id}:maintenance_overdue" for item_id in appliance_ids} <= fingerprints
    assert {f"inventory:{item_id}:low_stock" for item_id in inventory_ids} <= fingerprints


def test_investigation_lifecycle_is_independent_from_issue_resolution():
    initialize_database()
    with SessionLocal() as session:
        item = InventoryItem(
            name="Coffee",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        session.add(item)
        session.commit()
        item_id = item.id

    fingerprint = f"inventory:{item_id}:low_stock"
    issue = next(
        issue for issue in evaluate_monitoring("event", ["inventory"])
        if issue.fingerprint == fingerprint
    )
    with SessionLocal() as session:
        row = session.get(MonitoringIssue, issue.id)
        row.investigation_status = "provider_exhausted"
        session.commit()

    current = get_monitoring_issue(issue.id)
    assert current.issue_status == "open"
    assert current.investigation_status == "provider_exhausted"

    with SessionLocal() as session:
        item = session.get(InventoryItem, item_id)
        item.quantity = 5
        session.commit()
    resolved = next(
        issue for issue in evaluate_monitoring("scheduled", ["inventory"])
        if issue.fingerprint == fingerprint
    )
    assert resolved.issue_status == "resolved"
    assert resolved.investigation_status == "provider_exhausted"


def test_unknown_maintenance_status_does_not_resolve_existing_issue():
    initialize_database()
    with SessionLocal() as session:
        appliance = Appliance(
            name="Unknown maintenance",
            category="test",
            last_service_date=date(2024, 1, 1),
            service_interval_days=30,
            created_at=clock.now(),
        )
        session.add(appliance)
        session.commit()
        appliance_id = appliance.id

    issue = next(
        item
        for item in evaluate_monitoring("event", ["maintenance"])
        if item.fingerprint == f"appliance:{appliance_id}:maintenance_overdue"
    )
    with SessionLocal() as session:
        session.get(Appliance, appliance_id).last_service_date = None
        session.commit()
    evaluate_monitoring("scheduled", ["maintenance"])
    assert get_monitoring_issue(issue.id).issue_status == "open"


def test_unknown_warranty_status_does_not_resolve_existing_issue():
    initialize_database()
    with SessionLocal() as session:
        appliance = Appliance(
            name="Unknown warranty",
            category="test",
            warranty_end=date(2024, 1, 1),
            created_at=clock.now(),
        )
        session.add(appliance)
        session.commit()
        appliance_id = appliance.id

    issue = next(
        item
        for item in evaluate_monitoring("event", ["maintenance"])
        if item.fingerprint == f"appliance:{appliance_id}:warranty_expired"
    )
    with SessionLocal() as session:
        session.get(Appliance, appliance_id).warranty_end = None
        session.commit()
    evaluate_monitoring("scheduled", ["maintenance"])
    assert get_monitoring_issue(issue.id).issue_status == "open"


def test_monitoring_executor_bounds_capacity_and_prevents_duplicate_submission(monkeypatch):
    initialize_database()
    with SessionLocal() as session:
        first_item = InventoryItem(
            name="First item",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        second_item = InventoryItem(
            name="Second item",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        session.add_all([first_item, second_item])
        session.commit()
        first_id, second_id = first_item.id, second_item.id

    issues = evaluate_monitoring("manual", ["inventory"])
    first_issue = next(issue for issue in issues if issue.fingerprint == f"inventory:{first_id}:low_stock")
    second_issue = next(issue for issue in issues if issue.fingerprint == f"inventory:{second_id}:low_stock")

    started = Event()
    release = Event()

    def fake_run_agent(payload):
        started.set()
        release.wait(timeout=2)
        return {"id": "test-run", "stop_reason": "completed"}

    monkeypatch.setattr("app.services.monitoring_executor.run_agent", fake_run_agent)
    executor = MonitoringExecutor(max_workers=1, max_pending_jobs=0)
    executor.start()
    try:
        assert queue_issue_investigation(
            first_issue.id,
            goal="Investigate first inventory issue.",
            domains=["inventory"],
            executor=executor,
        )
        assert started.wait(timeout=2)
        assert not queue_issue_investigation(
            first_issue.id,
            goal="Duplicate investigation.",
            domains=["inventory"],
            executor=executor,
        )
        assert not queue_issue_investigation(
            second_issue.id,
            goal="Investigate second inventory issue.",
            domains=["inventory"],
            executor=executor,
        )
        assert get_monitoring_issue(second_issue.id).investigation_status == "interrupted"
    finally:
        release.set()
        executor.shutdown()


def test_monitoring_runtime_registers_non_overlapping_schedule(monkeypatch):
    class FakeScheduler:
        def __init__(self):
            self.job = None
            self.stopped = False

        def add_job(self, function, trigger, **kwargs):
            self.job = (function, trigger, kwargs)

        def start(self):
            return None

        def shutdown(self, wait=False):
            self.stopped = True

    scheduler = FakeScheduler()
    monkeypatch.setattr(
        "app.services.monitoring_runtime.BackgroundScheduler",
        lambda: scheduler,
    )
    runtime = MonitoringRuntime()
    runtime.start()
    try:
        assert scheduler.job is not None
        _, trigger, options = scheduler.job
        assert trigger == "interval"
        assert options["max_instances"] == 1
        assert options["coalesce"] is True
    finally:
        runtime.stop()
    assert scheduler.stopped


def test_scheduled_check_recovers_before_evaluating_and_protects_active_work(monkeypatch):
    events = []

    class FakeExecutor:
        def in_flight_investigation_ids(self):
            events.append("in_flight")
            return {"active-investigation"}

    runtime = MonitoringRuntime()
    runtime._executor = FakeExecutor()
    monkeypatch.setattr(
        "app.services.monitoring_runtime.recover_stale_investigations",
        lambda timeout, protected: events.append(("recover", protected)),
    )
    monkeypatch.setattr(
        "app.services.monitoring_runtime.monitor_and_investigate",
        lambda *args, **kwargs: events.append("evaluate"),
    )
    runtime.run_scheduled_check()
    assert events == ["in_flight", ("recover", {"active-investigation"}), "evaluate"]


def test_worker_initialization_failure_does_not_leave_issue_queued(monkeypatch):
    initialize_database()
    with SessionLocal() as session:
        item = InventoryItem(
            name="Initialization failure",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        session.add(item)
        session.commit()
        item_id = item.id
    issue = next(
        item
        for item in evaluate_monitoring("event", ["inventory"])
        if item.fingerprint == f"inventory:{item_id}:low_stock"
    )
    investigation_id = str(uuid4())
    with SessionLocal() as session:
        row = session.get(MonitoringIssue, issue.id)
        row.investigation_id = investigation_id
        row.investigation_status = "queued"
        session.commit()

    real_session_local = monitoring_executor_service.SessionLocal
    calls = 0

    def failing_initial_session():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("initial session failed")
        return real_session_local()

    monkeypatch.setattr(
        monitoring_executor_service,
        "SessionLocal",
        failing_initial_session,
    )
    MonitoringExecutor()._run_investigation(
        issue.id,
        investigation_id,
        "Investigate initialization failure.",
        ["inventory"],
    )
    assert get_monitoring_issue(issue.id).investigation_status == "failed"


def test_interrupted_investigation_retries_without_duplicate_agent_runs(monkeypatch):
    initialize_database()
    with SessionLocal() as session:
        item = InventoryItem(
            name="Retry investigation",
            quantity=1,
            unit="unit",
            reorder_threshold=2,
            created_at=clock.now(),
        )
        session.add(item)
        session.commit()
        item_id = item.id
    issue = next(
        item
        for item in evaluate_monitoring("event", ["inventory"])
        if item.fingerprint == f"inventory:{item_id}:low_stock"
    )
    with SessionLocal() as session:
        session.get(MonitoringIssue, issue.id).investigation_status = "interrupted"
        session.commit()

    started = Event()
    release = Event()
    calls = []

    def fake_run_agent(payload):
        calls.append(payload)
        started.set()
        release.wait(timeout=2)
        return {"id": "retry-run", "stop_reason": "completed"}

    monkeypatch.setattr("app.services.monitoring_executor.run_agent", fake_run_agent)
    monkeypatch.setattr(
        monitoring_service,
        "evaluate_monitoring",
        lambda *args, **kwargs: [get_monitoring_issue(issue.id)],
    )
    executor = MonitoringExecutor(max_workers=1, max_pending_jobs=0)
    executor.start()
    try:
        monitor_and_investigate("event", domains=["inventory"], executor=executor)
        assert started.wait(timeout=2)
        monitor_and_investigate("event", domains=["inventory"], executor=executor)
        assert len(calls) == 1
        assert get_monitoring_issue(issue.id).investigation_status == "investigating"
    finally:
        release.set()
        executor.shutdown()
