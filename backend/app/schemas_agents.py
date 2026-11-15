from typing import Any, Literal

from pydantic import BaseModel, Field

AgentDomain = Literal["energy", "water", "maintenance", "inventory"]
DecisionAction = Literal["investigate", "stop"]
RelationshipType = Literal["primary", "confirmed", "plausible"]


class SupervisorDecision(BaseModel):
    action: DecisionAction
    specialist: AgentDomain | None = None
    rationale: str
    next_investigation: str | None = None


class Finding(BaseModel):
    id: str
    category: str
    subject: str
    summary: str
    evidence: list[dict[str, Any]]
    severity: Literal["info", "low", "medium", "high"]
    confidence: float = Field(ge=0, le=1)
    possible_explanations: list[str]
    suggested_next_investigation: str | None = None
    suggested_action: str | None = None


class Recommendation(BaseModel):
    finding_ids: list[str] = Field(min_length=1)
    category: str
    subject: str
    summary: str
    suggested_action: str
    score: float = Field(ge=0, le=100)
    suppressed: bool = False
    suppression_reason: str | None = None
    status: Literal["active", "completed", "deferred", "dismissed"] = "active"


class UpdateRecommendationStatusRequest(BaseModel):
    status: Literal["active", "completed", "deferred", "dismissed"]


class InvestigationIssueContext(BaseModel):
    issue_id: str
    fingerprint: str
    issue_type: str
    domain: AgentDomain
    title: str
    relationship: RelationshipType
    relationship_reason: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    priority_factors: dict[str, int] = Field(default_factory=dict)


class InvestigationContext(BaseModel):
    primary_issue_id: str
    issues: list[InvestigationIssueContext] = Field(min_length=1, max_length=3)


class AgentRunCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=500)
    domains: list[AgentDomain] = Field(default_factory=list, max_length=3)
    investigation_context: InvestigationContext | None = None


class AgentRunOut(BaseModel):
    id: str
    goal: str
    domains: list[str]
    status: str
    mode: str
    trace: list[dict]
    findings: list[Finding]
    decisions: list[SupervisorDecision]
    stop_reason: str | None = None
    budgets: dict[str, int] = Field(default_factory=dict)
    recommendations: list[dict]
    investigation_context: InvestigationContext | None = None
    created_at: str
