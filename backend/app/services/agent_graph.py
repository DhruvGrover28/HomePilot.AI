from __future__ import annotations

import inspect
from typing import Protocol, TypedDict

import httpx
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.domain import priority_score
from app.schemas_agents import (
    Finding,
    InvestigationContext,
    Recommendation,
    SupervisorDecision,
)
from app.services.agent_tools import TOOLSETS
from app.services.provider_models import (
    FailoverDecisionModel,
    GeminiDecisionModel,
    GroqDecisionModel,
    OpenRouterDecisionModel,
    ProviderExhaustedError,
    ProviderDecisionModel,
)

LiveDecisionModel = GeminiDecisionModel


SUPERVISOR_BUDGET = 8
SPECIALIST_BUDGET = 5


class AgentState(TypedDict):
    goal: str
    requested_domains: list[str]
    remaining_domains: list[str]
    findings: list[dict]
    decisions: list[dict]
    trace: list[dict]
    current_domain: str | None
    supervisor_calls: int
    specialist_calls: dict[str, int]
    supervisor_budget: int
    specialist_budget: int
    status: str
    stop_reason: str | None
    recommendations: list[dict]
    investigation_context: InvestigationContext | None
    household_id: str | None


class DecisionModel(Protocol):
    def decide(self, state: AgentState) -> SupervisorDecision:
        ...


class MockDecisionModel:
    """Structured local decision model using capability similarity and findings."""

    def decide(self, state: AgentState) -> SupervisorDecision:
        available = state["remaining_domains"]
        findings = [Finding.model_validate(item) for item in state["findings"]]
        if not available:
            return SupervisorDecision(action="stop", rationale="No uninvestigated specialists remain.")
        if not findings:
            chosen = _best_capability_match(state["goal"], available)
            if chosen is None:
                return SupervisorDecision(action="stop", rationale="The goal does not match an available household capability.")
            return SupervisorDecision(
                action="investigate",
                specialist=chosen,
                rationale="The goal is semantically closest to the selected specialist capability.",
            )
        latest = findings[-1]
        if latest.suggested_next_investigation and latest.suggested_next_investigation in available:
            return SupervisorDecision(
                action="investigate",
                specialist=latest.suggested_next_investigation,
                rationale="The latest finding requests a targeted follow-up.",
                next_investigation=latest.suggested_next_investigation,
            )
        chosen = _best_capability_match(state["goal"], available)
        if chosen is not None:
            return SupervisorDecision(
                action="investigate",
                specialist=chosen,
                rationale="The remaining specialist has the strongest match to the goal after reviewing current evidence.",
            )
        return SupervisorDecision(
            action="stop",
            rationale="The available evidence is sufficient for the current goal.",
            next_investigation=latest.suggested_next_investigation,
        )


def _best_capability_match(goal: str, available: list[str]) -> str | None:
    descriptions = {
        "energy": {"electricity", "energy", "power", "spike", "consumption"},
        "water": {"water", "leak", "shower", "consumption"},
        "maintenance": {"maintenance", "service", "warranty", "appliance", "appliances"},
        "inventory": {"inventory", "stock", "supplies", "shopping", "reorder"},
    }
    words = {word.strip(".,!?").lower() for word in goal.split()}
    scores = {
        domain: len(words & descriptions[domain]) / max(1, len(descriptions[domain]))
        for domain in available
    }
    chosen = max(scores, key=scores.get)
    return chosen if scores[chosen] > 0 else None


def _decision_model() -> DecisionModel:
    settings = get_settings()
    if settings.llm_mode == "mock":
        return MockDecisionModel()
    if settings.llm_provider == "gemini" and not settings.gemini_api_key:
        raise RuntimeError("Live Gemini mode requires GEMINI_API_KEY.")
    if settings.llm_provider == "groq" and not settings.groq_api_key:
        raise RuntimeError("Live Groq mode requires GROQ_API_KEY.")
    if settings.llm_provider == "openrouter" and not settings.openrouter_api_key:
        raise RuntimeError("Live OpenRouter mode requires OPENROUTER_API_KEY.")
    return FailoverDecisionModel()


def _finding_for(domain: str, result: dict, finding_index: int) -> Finding:
    if domain in {"energy", "water"}:
        subject = "electricity consumption" if domain == "energy" else "water consumption"
        count = result["count"]
        anomaly = result["anomaly"]
        if count < 5:
            return Finding(
                id=f"{domain}-{finding_index}",
                category="consumption",
                subject=subject,
                summary=f"Only {count} historical periods are available.",
                evidence=[result],
                severity="info",
                confidence=0.3,
                possible_explanations=["The household has not supplied enough history."],
                suggested_next_investigation=None,
                suggested_action="Collect at least five comparable readings before diagnosing a trend.",
            )
        if anomaly.get("flagged"):
            return Finding(
                id=f"{domain}-{finding_index}",
                category="consumption",
                subject=subject,
                summary=f"A recent {subject} spike was detected.",
                evidence=[result],
                severity="high",
                confidence=0.9,
                possible_explanations=["A high-use appliance or a changed household routine."],
                suggested_next_investigation="maintenance" if domain == "energy" else None,
                suggested_action=f"Review the latest {subject} reading and contributing activity.",
            )
        return Finding(
            id=f"{domain}-{finding_index}",
            category="consumption",
            subject=subject,
            summary=f"No statistically significant {subject} anomaly was found.",
            evidence=[result],
            severity="info",
            confidence=0.8,
            possible_explanations=["Normal variation within the available history."],
            suggested_action="Continue collecting comparable readings.",
        )
    if domain == "maintenance":
        due = [item for item in result["items"] if item["warranty"]["status"] != "active" or item["maintenance"]["status"] in {"overdue", "due_soon"}]
        return Finding(
            id=f"maintenance-{finding_index}",
            category="maintenance",
            subject="appliance service and warranty",
            summary=f"{len(due)} of {len(result['items'])} appliances need attention.",
            evidence=[result],
            severity="medium" if due else "info",
            confidence=0.9,
            possible_explanations=["A warranty deadline or service interval is approaching or overdue."],
            suggested_action="Review the listed warranty and service deadlines." if due else "Continue monitoring appliance dates.",
        )
    low = [item for item in result["items"] if item["low"]]
    return Finding(
        id=f"inventory-{finding_index}",
        category="inventory",
        subject="household stock",
        summary=f"{len(low)} of {len(result['items'])} items are at or below threshold.",
        evidence=[result],
        severity="medium" if low else "info",
        confidence=0.95,
        possible_explanations=["Consumption has reduced stock below its configured reorder point."],
        suggested_action="Add low-stock items to the shopping list." if low else "Continue monitoring configured thresholds.",
    )


def _call_tool(tool, household_id: str | None) -> dict:
    try:
        sig = inspect.signature(tool)
        if "household_id" in sig.parameters:
            return tool(household_id=household_id)
        return tool()
    except (ValueError, TypeError):
        try:
            return tool(household_id=household_id)
        except TypeError:
            return tool()


def _run_specialist(state: AgentState, domain: str) -> tuple[list[dict], list[dict], int]:
    findings = list(state["findings"])
    trace = list(state["trace"])
    calls = state["specialist_calls"].get(domain, 0)
    household_id = state.get("household_id")
    for tool in TOOLSETS[domain]:
        if calls >= state["specialist_budget"]:
            trace.append(
                {
                    "kind": "budget_exhausted",
                    "scope": f"{domain}_specialist",
                    "reason": "specialist tool budget exhausted before the next tool call",
                }
            )
            return findings, trace, calls
        result = _call_tool(tool, household_id)
        calls += 1
        trace.append({"kind": "tool_call", "scope": f"{domain}_specialist", "tool": tool.__name__, "result": result})
        findings.append(_finding_for(domain, result, len(findings)).model_dump())
    return findings, trace, calls


def _recommendations(findings: list[dict]) -> tuple[list[dict], list[dict]]:
    proposals: list[dict] = []
    seen: set[tuple[str, str]] = set()
    trace: list[dict] = []
    severity_values = {"info": 0.1, "low": 0.35, "medium": 0.65, "high": 0.95}
    for raw in findings:
        finding = Finding.model_validate(raw)
        if finding.severity == "info" or not finding.suggested_action:
            continue
        key = (finding.category, finding.subject)
        score = priority_score(severity_values[finding.severity], finding.confidence, severity_values[finding.severity], 1, 0.5)
        proposal = Recommendation(
            finding_ids=[finding.id],
            category=finding.category,
            subject=finding.subject,
            summary=finding.summary,
            suggested_action=finding.suggested_action,
            score=score,
        )
        if key in seen:
            proposal.suppressed = True
            proposal.suppression_reason = "duplicate category and subject"
            trace.append({"kind": "recommendation_suppressed", "finding_id": finding.id, "reason": proposal.suppression_reason})
        else:
            seen.add(key)
        proposals.append(proposal.model_dump())
    return proposals, trace


def build_agent_graph(decision_model: DecisionModel):
    graph = StateGraph(AgentState)

    def decide(state: AgentState) -> dict:
        if state["status"] == "stopped":
            return {"current_domain": None}
        if state["supervisor_calls"] >= state["supervisor_budget"]:
            trace = list(state["trace"])
            trace.append({"kind": "budget_exhausted", "scope": "supervisor", "reason": "supervisor decision budget exhausted"})
            return {"status": "stopped", "stop_reason": "supervisor_budget_exhausted", "trace": trace}
        try:
            decision = decision_model.decide(state)
        except ProviderExhaustedError as exc:
            trace = list(state["trace"]) + exc.attempts
            trace.append(
                {
                    "kind": "provider_exhausted",
                    "reason": "All configured live providers failed.",
                    "attempts": exc.attempts,
                }
            )
            return {
                "status": "stopped",
                "stop_reason": "provider_exhausted",
                "trace": trace,
            }
        decisions = list(state["decisions"]) + [decision.model_dump()]
        provider_attempts = getattr(decision_model, "last_attempts", [])
        successful_attempt = next((item for item in reversed(provider_attempts) if item["success"]), None)
        trace = list(state["trace"]) + provider_attempts + [
            {
                "kind": "decision",
                "decision": decision.model_dump(),
                "findings_seen": len(state["findings"]),
                "context_issue_ids": [
                    item.issue_id for item in (state["investigation_context"].issues if state["investigation_context"] else [])
                ],
                "provider": successful_attempt["provider"] if successful_attempt else None,
                "model": successful_attempt["model"] if successful_attempt else None,
            }
        ]
        calls = state["supervisor_calls"] + 1
        if decision.action == "investigate" and decision.specialist in state["remaining_domains"]:
            remaining = [domain for domain in state["remaining_domains"] if domain != decision.specialist]
            return {
                "decisions": decisions,
                "trace": trace,
                "supervisor_calls": calls,
                "remaining_domains": remaining,
                "current_domain": decision.specialist,
            }
        return {
            "decisions": decisions,
            "trace": trace,
            "supervisor_calls": calls,
            "status": "completed",
            "stop_reason": decision.rationale,
        }

    def execute(state: AgentState) -> dict:
        domain = state["current_domain"]
        if domain is None:
            return {"status": "stopped", "stop_reason": "Supervisor did not select a specialist."}
        findings, trace, calls = _run_specialist(state, domain)
        exhausted = bool(trace and trace[-1].get("kind") == "budget_exhausted")
        return {
            "findings": findings,
            "trace": trace,
            "specialist_calls": {**state["specialist_calls"], domain: calls},
            "current_domain": None,
            "status": "stopped" if exhausted else "running",
            "stop_reason": "specialist_budget_exhausted" if exhausted else state["stop_reason"],
        }

    def finalize(state: AgentState) -> dict:
        recommendations, recommendation_trace = _recommendations(state["findings"])
        return {
            "status": state["status"],
            "recommendations": [item for item in recommendations if not item["suppressed"]],
            "trace": list(state["trace"]) + recommendation_trace,
            "investigation_context": state["investigation_context"],
            "household_id": state.get("household_id"),
        }

    graph.add_node("supervisor", decide)
    graph.add_node("specialist", execute)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: "specialist" if state["current_domain"] else "finalize",
        {"specialist": "specialist", "finalize": "finalize"},
    )
    graph.add_edge("specialist", "supervisor")
    graph.add_edge("finalize", END)
    return graph.compile()


def execute_agent(
    goal: str,
    domains: list[str],
    supervisor_budget: int = SUPERVISOR_BUDGET,
    specialist_budget: int = SPECIALIST_BUDGET,
    investigation_context: InvestigationContext | None = None,
    household_id: str | None = None,
) -> dict:
    state: AgentState = {
        "goal": goal,
        "requested_domains": domains,
        "remaining_domains": list(domains),
        "findings": [],
        "decisions": [],
        "trace": [],
        "current_domain": None,
        "supervisor_calls": 0,
        "specialist_calls": {},
        "supervisor_budget": supervisor_budget,
        "specialist_budget": specialist_budget,
        "status": "running",
        "stop_reason": None,
        "recommendations": [],
        "investigation_context": investigation_context,
        "household_id": household_id,
    }
    return build_agent_graph(_decision_model()).invoke(state)
