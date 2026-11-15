from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import select
from app import clock
from app.config import get_settings
from app.db.models import AgentRun
from app.db.session import SessionLocal
from app.schemas_agents import AgentRunCreate
from app.services.agent_graph import (
    SPECIALIST_BUDGET,
    SUPERVISOR_BUDGET,
    execute_agent,
)


DOMAINS = ("energy", "water", "maintenance", "inventory")


def run_agent(
    payload: AgentRunCreate,
    *,
    supervisor_budget: int = SUPERVISOR_BUDGET,
    specialist_budget: int = SPECIALIST_BUDGET,
    household_id: str | None = None,
) -> dict:
    settings = get_settings()
    if settings.llm_mode != "mock":
        if settings.llm_provider == "gemini" and not settings.gemini_api_key:
            raise RuntimeError("Live Gemini mode requires GEMINI_API_KEY.")
        if settings.llm_provider == "groq" and not settings.groq_api_key:
            raise RuntimeError("Live Groq mode requires GROQ_API_KEY.")
        if settings.llm_provider == "openrouter" and not settings.openrouter_api_key:
            raise RuntimeError("Live OpenRouter mode requires OPENROUTER_API_KEY.")
    domains = list(dict.fromkeys(payload.domains)) or list(DOMAINS)
    unknown = set(domains) - set(DOMAINS)
    if unknown:
        raise ValueError(f"Unsupported agent domain: {', '.join(sorted(unknown))}")
    result = execute_agent(
        payload.goal,
        domains,
        supervisor_budget,
        specialist_budget,
        payload.investigation_context,
        household_id=household_id,
    )
    with SessionLocal() as session:
        run = AgentRun(
            id=str(uuid4()),
            household_id=household_id,
            goal=payload.goal,
            domains=",".join(domains),
            status=result["status"],
            mode=settings.llm_mode,
            trace_json=json.dumps(
                {
                    "trace": result["trace"],
                    "findings": result["findings"],
                    "decisions": result["decisions"],
                    "stop_reason": result["stop_reason"],
                    "budgets": {
                        "supervisor": supervisor_budget,
                        "specialist": specialist_budget,
                    },
                    "investigation_context": (
                        result["investigation_context"].model_dump(mode="json")
                        if result.get("investigation_context")
                        else None
                    ),
                }
            ),
            recommendations_json=json.dumps(result["recommendations"]),
            created_at=clock.now(),
        )
        session.add(run)
        session.commit()
        return _serialize_run(run)


def _serialize_run(run: AgentRun) -> dict:
    stored = json.loads(run.trace_json)
    return {
        "id": run.id,
        "goal": run.goal,
        "domains": [domain for domain in run.domains.split(",") if domain],
        "status": run.status,
        "mode": run.mode,
        "trace": stored.get("trace", []),
        "findings": stored.get("findings", []),
        "decisions": stored.get("decisions", []),
        "stop_reason": stored.get("stop_reason"),
        "budgets": stored.get("budgets", {}),
        "recommendations": json.loads(run.recommendations_json),
        "investigation_context": stored.get("investigation_context"),
        "created_at": run.created_at.isoformat(),
    }


def get_agent_run(run_id: str, *, household_id: str | None = None) -> dict | None:
    with SessionLocal() as session:
        condition = (
            AgentRun.household_id == household_id
            if household_id is not None
            else AgentRun.household_id.is_(None)
        )
        run = session.scalar(
            select(AgentRun).where(
                AgentRun.id == run_id,
                condition,
            )
        )
        return _serialize_run(run) if run else None
