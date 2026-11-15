from __future__ import annotations

import json
from datetime import datetime
from threading import Lock
from typing import Iterable
from uuid import uuid4

from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import Appliance, InventoryItem, MonitoringIssue, Reading
from app.db.session import SessionLocal
from app.domain import consumption_stats, detect_anomaly, maintenance_status, warranty_status
from app.schemas_monitoring import MonitoringCandidate, MonitoringIssueOut, TriggerSource
from app.services.monitoring_executor import MonitoringExecutor


SUPPORTED_DOMAINS = ("energy", "water", "maintenance", "inventory")
_claim_lock = Lock()


def _reading_candidate(kind: str, rows: list[Reading]) -> MonitoringCandidate | None:
    if not rows:
        return None
    rates = [row.consumption / row.period_days for row in rows]
    anomaly = detect_anomaly(rates, rates[-1])
    if not anomaly.get("flagged"):
        return None
    latest = rows[-1]
    return MonitoringCandidate(
        fingerprint=f"{kind}:anomaly",
        issue_type="consumption_anomaly",
        domain=kind,
        title=f"Unusual {kind} consumption",
        evidence_id=latest.id,
        details={
            "latest_evidence_reading_id": latest.id,
            "reading_type": kind,
            "anomaly": anomaly,
            "statistics": consumption_stats(rates),
        },
    )


def _reading_is_resolvable(rows: list[Reading]) -> bool:
    if not rows:
        return False
    rates = [row.consumption / row.period_days for row in rows]
    anomaly = detect_anomaly(rates, rates[-1])
    return not anomaly.get("insufficient_data", False) and not anomaly.get("flagged", False)


def _maintenance_candidates(
    appliances: list[Appliance],
    today: datetime.date,
) -> tuple[list[MonitoringCandidate], set[str]]:
    settings = get_settings()
    candidates: list[MonitoringCandidate] = []
    resolvable: set[str] = set()
    for appliance in appliances:
        maintenance = maintenance_status(
            appliance.last_service_date,
            appliance.service_interval_days,
            today,
        )
        warranty = warranty_status(
            appliance.warranty_end,
            today,
            settings.warranty_warn_days,
        )
        maintenance_fingerprint = f"appliance:{appliance.id}:maintenance_overdue"
        warranty_fingerprint = f"appliance:{appliance.id}:warranty_expiring"
        expired_fingerprint = f"appliance:{appliance.id}:warranty_expired"
        if maintenance["status"] in {"due_soon", "overdue"}:
            candidates.append(
                MonitoringCandidate(
                    fingerprint=maintenance_fingerprint,
                    issue_type="maintenance_due",
                    domain="maintenance",
                    entity_id=appliance.id,
                    title=f"Maintenance due for {appliance.name}",
                    details={"appliance_id": appliance.id, "maintenance": maintenance},
                )
            )
        elif maintenance["status"] == "ok":
            resolvable.add(maintenance_fingerprint)
        if warranty["status"] == "expiring_soon":
            candidates.append(
                MonitoringCandidate(
                    fingerprint=warranty_fingerprint,
                    issue_type="warranty_expiring",
                    domain="maintenance",
                    entity_id=appliance.id,
                    title=f"Warranty expiring for {appliance.name}",
                    details={"appliance_id": appliance.id, "warranty": warranty},
                )
            )
        elif warranty["status"] == "active":
            resolvable.add(warranty_fingerprint)
        if warranty["status"] == "expired":
            candidates.append(
                MonitoringCandidate(
                    fingerprint=expired_fingerprint,
                    issue_type="warranty_expired",
                    domain="maintenance",
                    entity_id=appliance.id,
                    title=f"Warranty expired for {appliance.name}",
                    details={"appliance_id": appliance.id, "warranty": warranty},
                )
            )
        elif warranty["status"] == "active":
            resolvable.add(expired_fingerprint)
    return candidates, resolvable


def _inventory_candidates(items: list[InventoryItem]) -> tuple[list[MonitoringCandidate], set[str]]:
    candidates: list[MonitoringCandidate] = []
    resolvable: set[str] = set()
    for item in items:
        fingerprint = f"inventory:{item.id}:low_stock"
        if item.quantity <= item.reorder_threshold:
            candidates.append(
                MonitoringCandidate(
                    fingerprint=fingerprint,
                    issue_type="low_stock",
                    domain="inventory",
                    entity_id=item.id,
                    title=f"Low inventory: {item.name}",
                    details={
                        "inventory_item_id": item.id,
                        "quantity": item.quantity,
                        "reorder_threshold": item.reorder_threshold,
                        "unit": item.unit,
                    },
                )
            )
        else:
            resolvable.add(fingerprint)
    return candidates, resolvable


def _domains_or_all(domains: Iterable[str] | None) -> set[str]:
    selected = set(domains or SUPPORTED_DOMAINS)
    unknown = selected - set(SUPPORTED_DOMAINS)
    if unknown:
        raise ValueError(f"Unsupported monitoring domain: {', '.join(sorted(unknown))}")
    return selected


def _serialize_issue(issue: MonitoringIssue) -> MonitoringIssueOut:
    return MonitoringIssueOut(
        id=issue.id,
        fingerprint=issue.fingerprint,
        issue_type=issue.issue_type,
        domain=issue.domain,
        entity_id=issue.entity_id,
        title=issue.title,
        issue_status=issue.issue_status,
        first_trigger_source=issue.first_trigger_source,
        last_trigger_source=issue.last_trigger_source,
        first_detected_at=issue.first_detected_at,
        last_detected_at=issue.last_detected_at,
        resolved_at=issue.resolved_at,
        occurrence_count=issue.occurrence_count,
        latest_evidence_id=issue.latest_evidence_id,
        details=json.loads(issue.details_json),
        investigation_id=issue.investigation_id,
        investigation_status=issue.investigation_status,
        active_run_id=issue.active_run_id,
        latest_run_id=issue.latest_run_id,
        claimed_at=issue.claimed_at,
        started_at=issue.started_at,
        completed_at=issue.completed_at,
        last_error=issue.last_error,
    )


def _upsert_candidate(
    session,
    candidate: MonitoringCandidate,
    trigger_source: TriggerSource,
    detected_at: datetime,
) -> MonitoringIssue:
    issue = session.scalar(
        select(MonitoringIssue).where(MonitoringIssue.fingerprint == candidate.fingerprint)
    )
    details_json = json.dumps(candidate.details)
    if issue is None:
        issue = MonitoringIssue(
            id=str(uuid4()),
            fingerprint=candidate.fingerprint,
            issue_type=candidate.issue_type,
            domain=candidate.domain,
            entity_id=candidate.entity_id,
            title=candidate.title,
            issue_status="open",
            first_trigger_source=trigger_source,
            last_trigger_source=trigger_source,
            first_detected_at=detected_at,
            last_detected_at=detected_at,
            created_at=detected_at,
            occurrence_count=1,
            latest_evidence_id=candidate.evidence_id,
            details_json=details_json,
            investigation_status="not_started",
        )
        session.add(issue)
        return issue
    if issue.issue_status == "resolved":
        issue.issue_status = "open"
        issue.resolved_at = None
        issue.investigation_status = "not_started"
        issue.investigation_id = None
        issue.active_run_id = None
        issue.claimed_at = None
        issue.started_at = None
        issue.completed_at = None
        issue.last_error = None
    issue.last_trigger_source = trigger_source
    issue.last_detected_at = detected_at
    issue.occurrence_count += 1
    issue.latest_evidence_id = candidate.evidence_id
    issue.details_json = details_json
    issue.title = candidate.title
    return issue


def _resolve_issues(
    session,
    domains: set[str],
    resolvable_fingerprints: set[str],
    resolved_at: datetime,
) -> None:
    if not resolvable_fingerprints:
        return
    issues = session.scalars(
        select(MonitoringIssue).where(
            MonitoringIssue.issue_status == "open",
            MonitoringIssue.domain.in_(domains),
            MonitoringIssue.fingerprint.in_(resolvable_fingerprints),
        )
    ).all()
    for issue in issues:
        issue.issue_status = "resolved"
        issue.resolved_at = resolved_at


def evaluate_monitoring(
    trigger_source: TriggerSource,
    domains: Iterable[str] | None = None,
) -> list[MonitoringIssueOut]:
    selected = _domains_or_all(domains)
    detected_at = clock.now()
    candidates: list[MonitoringCandidate] = []
    resolvable_fingerprints: set[str] = set()
    with SessionLocal() as session:
        if "energy" in selected:
            rows = session.scalars(
                select(Reading)
                .where(Reading.type == "electricity")
                .order_by(Reading.reading_date, Reading.id)
            ).all()
            candidate = _reading_candidate("energy", rows)
            if candidate:
                candidates.append(candidate)
            elif _reading_is_resolvable(rows):
                resolvable_fingerprints.add("energy:anomaly")
        if "water" in selected:
            rows = session.scalars(
                select(Reading)
                .where(Reading.type == "water")
                .order_by(Reading.reading_date, Reading.id)
            ).all()
            candidate = _reading_candidate("water", rows)
            if candidate:
                candidates.append(candidate)
            elif _reading_is_resolvable(rows):
                resolvable_fingerprints.add("water:anomaly")
        if "maintenance" in selected:
            maintenance_candidates, maintenance_resolvable = _maintenance_candidates(
                session.scalars(select(Appliance).order_by(Appliance.id)).all(),
                detected_at.date(),
            )
            candidates.extend(maintenance_candidates)
            resolvable_fingerprints.update(maintenance_resolvable)
        if "inventory" in selected:
            inventory_candidates, inventory_resolvable = _inventory_candidates(
                session.scalars(select(InventoryItem).order_by(InventoryItem.id)).all()
            )
            candidates.extend(inventory_candidates)
            resolvable_fingerprints.update(inventory_resolvable)
        for candidate in candidates:
            _upsert_candidate(session, candidate, trigger_source, detected_at)
        _resolve_issues(session, selected, resolvable_fingerprints, detected_at)
        session.commit()
        fingerprints = {candidate.fingerprint for candidate in candidates} | resolvable_fingerprints
        issues = session.scalars(
            select(MonitoringIssue)
            .where(
                MonitoringIssue.domain.in_(selected),
                MonitoringIssue.fingerprint.in_(fingerprints),
            )
            .order_by(MonitoringIssue.last_detected_at.desc())
        ).all()
        return [_serialize_issue(issue) for issue in issues]


def list_monitoring_issues(
    *,
    issue_status: str | None = None,
) -> list[MonitoringIssueOut]:
    with SessionLocal() as session:
        query = select(MonitoringIssue).order_by(MonitoringIssue.last_detected_at.desc())
        if issue_status:
            if issue_status not in {"open", "resolved"}:
                raise ValueError("issue_status must be open or resolved.")
            query = query.where(MonitoringIssue.issue_status == issue_status)
        return [_serialize_issue(issue) for issue in session.scalars(query).all()]


def get_monitoring_issue(issue_id: str) -> MonitoringIssueOut | None:
    with SessionLocal() as session:
        issue = session.get(MonitoringIssue, issue_id)
        return _serialize_issue(issue) if issue else None


def queue_issue_investigation(
    issue_id: str,
    *,
    goal: str,
    domains: list[str],
    executor: MonitoringExecutor,
) -> bool:
    with _claim_lock:
        investigation_id = str(uuid4())
        with SessionLocal() as session:
            issue = session.get(MonitoringIssue, issue_id)
            if issue is None or issue.issue_status != "open":
                return False
            if issue.investigation_status in {"queued", "investigating"}:
                return False
            issue.investigation_id = investigation_id
            issue.investigation_status = "queued"
            issue.claimed_at = clock.now()
            issue.started_at = None
            issue.completed_at = None
            issue.active_run_id = None
            issue.last_error = None
            session.commit()
        return executor.submit(issue_id, investigation_id, goal, domains)


def monitor_and_investigate(
    trigger_source: TriggerSource,
    *,
    domains: Iterable[str] | None,
    executor: MonitoringExecutor,
) -> list[MonitoringIssueOut]:
    issues = evaluate_monitoring(trigger_source, domains)
    for issue in issues:
        if issue.issue_status != "open":
            continue
        if issue.investigation_status not in {"not_started", "interrupted"}:
            continue
        queue_issue_investigation(
            issue.id,
            goal=f"Investigate household monitoring issue: {issue.title}.",
            domains=[issue.domain],
            executor=executor,
        )
    refreshed: list[MonitoringIssueOut] = []
    for issue in issues:
        current = get_monitoring_issue(issue.id)
        if current is not None:
            refreshed.append(current)
    return refreshed
