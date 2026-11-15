from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


IssueStatus = Literal["open", "resolved"]
InvestigationStatus = Literal[
    "not_started",
    "queued",
    "investigating",
    "completed",
    "provider_exhausted",
    "failed",
    "interrupted",
]
TriggerSource = Literal["scheduled", "event", "manual"]
RelationshipType = Literal["confirmed", "plausible", "unrelated"]


class MonitoringRelationship(BaseModel):
    relationship: RelationshipType
    reason: str


class MonitoringCandidate(BaseModel):
    fingerprint: str
    issue_type: str
    domain: str
    entity_id: int | None = None
    title: str
    evidence_id: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MonitoringIssueOut(BaseModel):
    id: str
    fingerprint: str
    issue_type: str
    domain: str
    entity_id: int | None
    title: str
    issue_status: IssueStatus
    first_trigger_source: TriggerSource
    last_trigger_source: TriggerSource
    first_detected_at: datetime
    last_detected_at: datetime
    resolved_at: datetime | None
    occurrence_count: int
    latest_evidence_id: int | None
    details: dict[str, Any]
    investigation_id: str | None
    investigation_status: InvestigationStatus
    active_run_id: str | None
    latest_run_id: str | None
    claimed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
