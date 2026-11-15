from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import delete, select

from app import clock
from app.config import get_settings
from app.db.models import AgentRun, AssistantMessage
from app.db.session import SessionLocal
from app.schemas_agents import AgentRunCreate
from app.services.agent_service import run_agent
from app.services.agent_tools import (
    energy_readings,
    inventory_levels,
    maintenance_statuses,
    water_readings,
)
from app.services.household_intelligence import build_household_intelligence
from app.services.monitoring import list_monitoring_issues


def _build_deterministic_reply(
    message: str,
    household_id: str,
) -> dict:
    msg = message.lower().strip()
    energy = energy_readings(household_id)
    water = water_readings(household_id)
    maintenance = maintenance_statuses(household_id)
    inventory = inventory_levels(household_id)
    open_issues = list_monitoring_issues(issue_status="open", household_id=household_id)
    intel = build_household_intelligence(household_id)

    suggested_prompts = [
        "What household issues should I prioritize?",
        "Are any appliances due for maintenance?",
        "Which supplies are running low?",
        "How is our electricity consumption trending?",
    ]
    related_issues: list[dict] = []
    related_recs: list[dict] = []
    agent_run_data: dict | None = None

    # Check if user wants a full investigation
    if any(keyword in msg for keyword in ("investigate", "run analysis", "deep dive")):
        domains = []
        if any(w in msg for w in ("energy", "electricity", "power")):
            domains.append("energy")
        if any(w in msg for w in ("water", "leak")):
            domains.append("water")
        if any(w in msg for w in ("maintenance", "appliance", "service", "warranty")):
            domains.append("maintenance")
        if any(w in msg for w in ("inventory", "stock", "supplies")):
            domains.append("inventory")
        if not domains:
            domains = ["energy", "maintenance"]

        payload = AgentRunCreate(goal=message[:200], domains=domains)
        run_result = run_agent(payload, household_id=household_id)
        agent_run_data = run_result

        reply = (
            f"I completed an agentic investigation with our specialist agents for {', '.join(domains)}. "
            f"Supervisor status: {run_result['status']} ({run_result['mode']} mode). "
            f"Findings identified: {len(run_result.get('findings', []))}. "
            f"Evidence-backed recommendations: {len(run_result.get('recommendations', []))}."
        )
        if run_result.get("recommendations"):
            related_recs = run_result["recommendations"][:3]
        return {
            "reply": reply,
            "suggested_prompts": [
                "Explain the latest recommendation.",
                "Inspect the investigation trace.",
                "What should I prioritize next?",
            ],
            "related_issues": [issue.model_dump() for issue in open_issues[:3]],
            "related_recommendations": related_recs,
            "agent_run": agent_run_data,
        }

    # Energy questions
    if any(w in msg for w in ("energy", "electricity", "power", "kwh")):
        count = energy.get("count", 0)
        anomaly = energy.get("anomaly", {})
        rates = energy.get("rates", [])
        avg = round(sum(rates) / len(rates), 2) if rates else 0
        if count == 0:
            reply = "You haven't recorded any electricity readings yet. Add readings in the Energy section or use 'Seed simulated demo' to populate sample data."
        elif anomaly.get("flagged"):
            pct = anomaly.get("percent_change", 0)
            reply = f"Electricity consumption shows an abnormal spike (+{pct}% vs baseline). Latest daily rate is {rates[-1]} kWh compared to historical average of {avg} kWh. I recommend investigating whether a high-power appliance (like heating or cooling) is responsible."
        else:
            reply = f"Electricity consumption is currently normal across {count} recorded periods. Average rate is {avg} kWh/day, with the latest recorded rate at {rates[-1]} kWh/day."
        related_issues = [issue.model_dump() for issue in open_issues if issue.domain == "energy"]

    # Water questions
    elif any(w in msg for w in ("water", "litres", "shower", "leak")):
        count = water.get("count", 0)
        anomaly = water.get("anomaly", {})
        rates = water.get("rates", [])
        avg = round(sum(rates) / len(rates), 2) if rates else 0
        if count == 0:
            reply = "No water readings have been recorded yet. You can log manual readings or import CSV data in the Water section."
        elif anomaly.get("flagged"):
            pct = anomaly.get("percent_change", 0)
            reply = f"Water usage was flagged for an abnormal increase (+{pct}%). Latest rate is {rates[-1]} litres/day vs average of {avg} litres/day. Please check for leaking fixtures or running toilets."
        else:
            reply = f"Water consumption is stable. Across {count} recorded periods, your average rate is {avg} litres/day, with latest at {rates[-1]} litres/day."
        related_issues = [issue.model_dump() for issue in open_issues if issue.domain == "water"]

    # Maintenance questions
    elif any(w in msg for w in ("maintenance", "appliance", "service", "warranty")):
        items = maintenance.get("items", [])
        if not items:
            reply = "You have no appliances registered. Add your home appliances in the Maintenance section to track service intervals and warranties."
        else:
            attention = [
                i for i in items
                if i["warranty"]["status"] != "active" or i["maintenance"]["status"] in ("overdue", "due_soon")
            ]
            if attention:
                details = ", ".join(f"{i['appliance']} ({i['maintenance']['status']} service, {i['warranty']['status']} warranty)" for i in attention[:3])
                reply = f"There are {len(attention)} appliances requiring attention: {details}."
            else:
                reply = f"All {len(items)} appliances are up to date with active warranties and no overdue service intervals."
        related_issues = [issue.model_dump() for issue in open_issues if issue.domain == "maintenance"]

    # Inventory questions
    elif any(w in msg for w in ("inventory", "supplies", "stock", "shopping")):
        items = inventory.get("items", [])
        low = [i for i in items if i.get("low")]
        if not items:
            reply = "Your household inventory is empty. Add essential supplies in the Inventory section to track stock thresholds."
        elif low:
            names = ", ".join(f"{i['item']} ({i['quantity']} {i['unit']})" for i in low)
            reply = f"The following items are at or below reorder threshold: {names}. I recommend adding them to your shopping list."
        else:
            reply = f"All {len(items)} tracked inventory items are currently above their reorder thresholds."
        related_issues = [issue.model_dump() for issue in open_issues if issue.domain == "inventory"]

    # Priority / summary questions
    elif any(w in msg for w in ("priorit", "summary", "overview", "status", "what to do")):
        open_count = len(open_issues)
        recs = intel.get("recommendations", [])
        top_recs = [r["recommendation"]["suggested_action"] for r in recs[:3]]
        if open_count == 0:
            reply = "Your household is currently in great shape with 0 detected monitoring issues and all resources operating normally."
        else:
            rec_text = f" Suggested next actions: {'; '.join(top_recs)}." if top_recs else ""
            reply = f"There are currently {open_count} open monitoring issue(s).{rec_text}"
        related_issues = [issue.model_dump() for issue in open_issues[:3]]
        related_recs = [r["recommendation"] for r in recs[:3]]

    # General greeting or help
    else:
        reply = (
            "Hello! I am HomePilot Assistant. I coordinate with our Energy, Water, Maintenance, and Inventory "
            "specialists to monitor your household operations. You can ask me about consumption trends, appliance "
            "warranties, low stock, or ask me to investigate an issue."
        )

    return {
        "reply": reply,
        "suggested_prompts": suggested_prompts,
        "related_issues": related_issues,
        "related_recommendations": related_recs,
        "agent_run": None,
    }


def handle_assistant_message(
    user_message: str,
    household_id: str,
) -> dict:
    now = clock.now()
    user_msg_id = str(uuid4())
    assistant_msg_id = str(uuid4())

    # Build response
    result = _build_deterministic_reply(user_message, household_id)

    # Persist in DB
    with SessionLocal() as session:
        user_msg = AssistantMessage(
            id=user_msg_id,
            household_id=household_id,
            role="user",
            content=user_message,
            metadata_json="{}",
            created_at=now,
        )
        assistant_msg = AssistantMessage(
            id=assistant_msg_id,
            household_id=household_id,
            role="assistant",
            content=result["reply"],
            metadata_json=json.dumps(
                {
                    "suggested_prompts": result["suggested_prompts"],
                    "related_issues": [i.get("id") for i in result.get("related_issues", [])],
                    "agent_run_id": result["agent_run"]["id"] if result.get("agent_run") else None,
                }
            ),
            created_at=clock.now(),
        )
        session.add_all([user_msg, assistant_msg])
        session.commit()

    return result


def get_assistant_history(household_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.household_id == household_id)
            .order_by(AssistantMessage.created_at.asc())
        ).all()
        return [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "metadata": json.loads(row.metadata_json),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]


def clear_assistant_history(household_id: str) -> None:
    with SessionLocal() as session:
        session.execute(
            delete(AssistantMessage).where(AssistantMessage.household_id == household_id)
        )
        session.commit()
