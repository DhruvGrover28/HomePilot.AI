from __future__ import annotations

from typing import Any, Iterable

from app.schemas_monitoring import MonitoringIssueOut


_SEVERITY_BY_TYPE = {
    "consumption_anomaly": 3,
    "maintenance_due": 3,
    "warranty_expired": 3,
    "low_stock": 3,
    "warranty_expiring": 2,
}


def _evidence_state(issue: MonitoringIssueOut) -> int:
    details = issue.details
    if issue.issue_type in {"maintenance_due", "warranty_expiring", "warranty_expired"}:
        status = details.get("maintenance", details.get("warranty", {})).get("status")
        return 0 if status == "unknown" else 1
    anomaly = details.get("anomaly", {})
    if anomaly.get("insufficient_data") is True:
        return 0
    if issue.issue_type == "consumption_anomaly":
        return 1 if anomaly.get("flagged") is True else 0
    if issue.issue_type == "low_stock":
        return 1 if {"quantity", "reorder_threshold"} <= details.keys() else 0
    return 0


def _urgency_level(issue: MonitoringIssueOut) -> int:
    if issue.issue_type in {"warranty_expired", "low_stock", "maintenance_due"}:
        return 3
    if issue.issue_type == "warranty_expiring":
        return 2
    return 1


def _impact_level(issue: MonitoringIssueOut) -> int:
    details = issue.details
    if issue.issue_type == "consumption_anomaly":
        change = abs(float(details.get("anomaly", {}).get("percent_change") or 0))
        return 3 if change >= 50 else 2 if change > 0 else 1
    if issue.issue_type == "low_stock":
        return 3 if float(details.get("quantity", 1)) <= 0 else 2
    return 2 if issue.issue_type in {"maintenance_due", "warranty_expired"} else 1


def monitoring_priority_factors(issue: MonitoringIssueOut) -> dict[str, int]:
    evidence_state = _evidence_state(issue)
    return {
        "evidence_state": evidence_state,
        "severity": _SEVERITY_BY_TYPE.get(issue.issue_type, 1),
        "urgency": _urgency_level(issue),
        "impact": _impact_level(issue),
        "confidence": 2 if evidence_state else 0,
        "evidence_completeness": 2 if evidence_state else 0,
        "corroboration": 0,
        "actionability": 1 if evidence_state else 0,
    }


def monitoring_priority_key(
    issue: MonitoringIssueOut,
    *,
    corroboration_level: int = 0,
) -> tuple[Any, ...]:
    factors = monitoring_priority_factors(issue)
    factors["corroboration"] = max(0, min(2, corroboration_level))
    return (
        factors["evidence_state"],
        factors["severity"],
        factors["urgency"],
        factors["impact"],
        factors["confidence"],
        factors["evidence_completeness"],
        factors["corroboration"],
        factors["actionability"],
        issue.fingerprint,
    )


_RECOMMENDATION_STATUS = {
    "active": 3,
    "deferred": 2,
    "completed": 0,
    "suppressed": 0,
    "dismissed": 0,
    "superseded": 0,
}


def recommendation_priority_factors(
    recommendation: dict[str, Any],
    findings: Iterable[dict[str, Any]],
    source_issue: MonitoringIssueOut | None,
) -> dict[str, int]:
    linked_ids = set(recommendation.get("finding_ids") or [])
    linked_findings = [
        finding for finding in findings if finding.get("id") in linked_ids
    ]
    severities = [
        {"info": 0, "low": 1, "medium": 2, "high": 3}.get(
            finding.get("severity"), 0
        )
        for finding in linked_findings
    ]
    confidence = [
        float(finding.get("confidence", 0))
        for finding in linked_findings
        if isinstance(finding.get("confidence"), (int, float))
    ]
    evidence_support = (
        2
        if linked_findings
        and all(finding.get("evidence") for finding in linked_findings)
        and confidence
        and min(confidence) >= 0.8
        else 1
        if linked_findings and any(finding.get("evidence") for finding in linked_findings)
        else 0
    )
    suggested_action = str(recommendation.get("suggested_action") or "").strip()
    feasibility = 2 if suggested_action else 0
    status = str(
        recommendation.get("status")
        or ("suppressed" if recommendation.get("suppressed") else "active")
    )
    return {
        "recommendation_status": _RECOMMENDATION_STATUS.get(status, 0),
        "benefit": min(3, max(severities, default=0)),
        "urgency": (
            monitoring_priority_factors(source_issue)["urgency"]
            if source_issue is not None
            else 0
        ),
        "evidence_support": evidence_support,
        "feasibility": feasibility,
    }


def recommendation_priority_key(
    recommendation: dict[str, Any],
    findings: Iterable[dict[str, Any]],
    source_issue: MonitoringIssueOut | None,
    *,
    recommendation_id: str,
) -> tuple[Any, ...]:
    factors = recommendation_priority_factors(recommendation, findings, source_issue)
    source_priority = monitoring_priority_key(source_issue) if source_issue else ()
    return (
        factors["recommendation_status"],
        factors["benefit"],
        factors["urgency"],
        factors["evidence_support"],
        factors["feasibility"],
        source_priority,
        recommendation_id,
    )
