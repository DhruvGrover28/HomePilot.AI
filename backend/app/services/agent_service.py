from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import AgentRun, Appliance, InventoryItem, Reading
from app.db.session import SessionLocal
from app.domain import consumption_stats, maintenance_status, warranty_status
from app.schemas_agents import AgentRunCreate

DOMAINS = ("energy", "maintenance", "inventory")


def _energy_analysis(readings: list[Reading]) -> dict:
    electricity = [row for row in readings if row.type == "electricity"]
    rates = [row.consumption / row.period_days for row in electricity]
    stats = consumption_stats(rates)
    return {
        "domain": "energy",
        "title": "Energy review",
        "summary": f"{len(electricity)} electricity periods analyzed.",
        "metrics": stats,
        "recommendation": (
            "Continue monitoring daily electricity use."
            if not electricity
            else f"Average electricity use is {float(stats['mean']):.2f} kWh/day."
        ),
        "severity": "info",
    }


def _maintenance_analysis(appliances: list[Appliance], today: date) -> dict:
    due = []
    for appliance in appliances:
        warranty = warranty_status(appliance.warranty_end, today, get_settings().warranty_warn_days)
        maintenance = maintenance_status(appliance.last_service_date, appliance.service_interval_days, today)
        if warranty["status"] in {"expired", "expiring_soon"} or maintenance["status"] in {"overdue", "due_soon"}:
            due.append({"appliance": appliance.name, "warranty": warranty, "maintenance": maintenance})
    return {
        "domain": "maintenance",
        "title": "Maintenance review",
        "summary": f"{len(due)} of {len(appliances)} appliances need attention.",
        "items": due,
        "recommendation": "Review the listed warranty or service deadlines." if due else "No urgent maintenance action found.",
        "severity": "warning" if due else "info",
    }


def _inventory_analysis(items: list[InventoryItem]) -> dict:
    low_stock = [
        {"item": item.name, "quantity": item.quantity, "threshold": item.reorder_threshold, "unit": item.unit}
        for item in items
        if item.quantity <= item.reorder_threshold
    ]
    return {
        "domain": "inventory",
        "title": "Inventory review",
        "summary": f"{len(low_stock)} of {len(items)} items are at or below reorder threshold.",
        "items": low_stock,
        "recommendation": "Add low-stock items to the shopping list." if low_stock else "Inventory levels are above configured thresholds.",
        "severity": "warning" if low_stock else "info",
    }


def run_agent(payload: AgentRunCreate) -> dict:
    settings = get_settings()
    if settings.llm_mode != "mock":
        raise RuntimeError("Live agent mode is not configured; use LLM_MODE=mock.")
    domains = list(dict.fromkeys(payload.domains)) or list(DOMAINS)
    unknown = set(domains) - set(DOMAINS)
    if unknown:
        raise ValueError(f"Unsupported agent domain: {', '.join(sorted(unknown))}")

    with SessionLocal() as session:
        readings = session.scalars(select(Reading).order_by(Reading.reading_date)).all()
        appliances = session.scalars(select(Appliance).order_by(Appliance.name)).all()
        items = session.scalars(select(InventoryItem).order_by(InventoryItem.name)).all()
        trace = [
            {"node": "supervisor", "status": "completed", "selected_domains": domains},
        ]
        recommendations = []
        for domain in domains:
            trace.append({"node": f"{domain}_specialist", "status": "completed"})
            if domain == "energy":
                recommendations.append(_energy_analysis(readings))
            elif domain == "maintenance":
                recommendations.append(_maintenance_analysis(appliances, clock.now().date()))
            else:
                recommendations.append(_inventory_analysis(items))

        run = AgentRun(
            id=str(uuid4()),
            goal=payload.goal,
            domains=",".join(domains),
            status="completed",
            mode=settings.llm_mode,
            trace_json=json.dumps(trace),
            recommendations_json=json.dumps(recommendations),
            created_at=clock.now(),
        )
        session.add(run)
        session.commit()
        return _serialize_run(run)


def _serialize_run(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "goal": run.goal,
        "domains": [domain for domain in run.domains.split(",") if domain],
        "status": run.status,
        "mode": run.mode,
        "trace": json.loads(run.trace_json),
        "recommendations": json.loads(run.recommendations_json),
        "created_at": run.created_at.isoformat(),
    }


def get_agent_run(run_id: str) -> dict | None:
    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        return _serialize_run(run) if run else None
