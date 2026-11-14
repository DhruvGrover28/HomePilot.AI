from __future__ import annotations

import json
from typing import Protocol, TypedDict

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.domain import priority_score
from app.schemas_agents import Finding, Recommendation, SupervisorDecision
from app.services.agent_tools import TOOLSETS


SUPERVISOR_BUDGET = 8
SPECIALIST_BUDGET = 5


def _groq_decision_schema() -> dict:
    schema = SupervisorDecision.model_json_schema()
    schema["required"] = list(schema["properties"])
    schema["additionalProperties"] = False
    return schema


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


class DecisionModel(Protocol):
    def decide(self, state: AgentState) -> SupervisorDecision:
        ...


class LiveDecisionModel:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("Live Gemini mode requires GEMINI_API_KEY.")
        model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0,
            timeout=60,
            max_retries=0,
        )
        self._structured = model.with_structured_output(SupervisorDecision)

    def decide(self, state: AgentState) -> SupervisorDecision:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a bounded household investigation supervisor. "
                    "Choose investigate only when evidence or the goal justifies it. "
                    "You may stop, choose one available specialist, or choose another after findings. "
                    "Never perform tools or modify data. Return only the requested structured decision.",
                ),
                (
                    "human",
                    "Goal: {goal}\nAvailable specialists: {available}\n"
                    "Previous decisions: {decisions}\nFindings from tools: {findings}\n"
                    "Supervisor calls remaining: {remaining_budget}\n"
                    "Select a specialist only from Available specialists.",
                ),
            ]
        )
        return self._structured.invoke(
            prompt.format_messages(
                goal=state["goal"],
                available=state["remaining_domains"],
                decisions=json.dumps(state["decisions"]),
                findings=json.dumps(state["findings"]),
                remaining_budget=state["supervisor_budget"] - state["supervisor_calls"],
            )
        )


class GroqDecisionModel:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise RuntimeError("Live Groq mode requires GROQ_API_KEY.")
        self._api_key = settings.groq_api_key
        self._model = settings.groq_model

    def decide(self, state: AgentState) -> SupervisorDecision:
        prompt = (
            "You are a bounded household investigation supervisor. "
            "Return one JSON object matching the supplied schema. "
            "Choose investigate only when evidence or the goal justifies it. "
            "You may stop, choose one available specialist, or choose another after findings. "
            "Never perform tools or modify data. "
            f"Goal: {state['goal']}\n"
            f"Available specialists: {state['remaining_domains']}\n"
            f"Previous decisions: {json.dumps(state['decisions'])}\n"
            f"Findings from tools: {json.dumps(state['findings'])}\n"
            f"Supervisor calls remaining: {state['supervisor_budget'] - state['supervisor_calls']}\n"
        )
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_completion_tokens": 1024,
                    "reasoning_effort": "low",
                    "include_reasoning": False,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "supervisor_decision",
                            "strict": True,
                            "schema": _groq_decision_schema(),
                        },
                    },
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"].get("content") or ""
            if not content:
                raise RuntimeError("Groq returned an empty Supervisor decision.")
            return SupervisorDecision.model_validate_json(content)
        except httpx.HTTPError as exc:
            raise RuntimeError("Groq Supervisor request failed.") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Groq returned an invalid Supervisor decision.") from exc


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
        "maintenance": {"maintenance", "service", "warranty", "appliance"},
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
    if settings.llm_provider == "groq":
        return GroqDecisionModel()
    if settings.llm_provider == "gemini":
        return LiveDecisionModel()
    raise RuntimeError(f"Unsupported live LLM provider: {settings.llm_provider}")


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


def _run_specialist(state: AgentState, domain: str) -> tuple[list[dict], list[dict], int]:
    findings = list(state["findings"])
    trace = list(state["trace"])
    calls = state["specialist_calls"].get(domain, 0)
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
        result = tool()
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
        decision = decision_model.decide(state)
        decisions = list(state["decisions"]) + [decision.model_dump()]
        trace = list(state["trace"]) + [{"kind": "decision", "decision": decision.model_dump(), "findings_seen": len(state["findings"])}]
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


def execute_agent(goal: str, domains: list[str], supervisor_budget: int = SUPERVISOR_BUDGET, specialist_budget: int = SPECIALIST_BUDGET) -> dict:
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
    }
    return build_agent_graph(_decision_model()).invoke(state)
