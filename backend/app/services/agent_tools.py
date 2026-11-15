from __future__ import annotations

from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import Appliance, InventoryItem, Reading
from app.db.session import SessionLocal
from app.domain import consumption_stats, detect_anomaly, maintenance_status, warranty_status


def energy_readings(household_id: str | None = None) -> dict:
    if not household_id:
        return {
            "type": "energy_readings",
            "count": 0,
            "latest_date": None,
            "rates": [],
            "statistics": consumption_stats([]),
            "anomaly": {"insufficient_data": True},
        }
    with SessionLocal() as session:
        query = select(Reading).where(Reading.type == "electricity", Reading.household_id == household_id)
        rows = session.scalars(query.order_by(Reading.reading_date)).all()
    rates = [row.consumption / row.period_days for row in rows]
    anomaly = detect_anomaly(rates, rates[-1]) if rates else {"insufficient_data": True}
    return {
        "type": "energy_readings",
        "count": len(rows),
        "latest_date": rows[-1].reading_date.isoformat() if rows else None,
        "rates": rates,
        "statistics": consumption_stats(rates),
        "anomaly": anomaly,
    }


def water_readings(household_id: str | None = None) -> dict:
    if not household_id:
        return {
            "type": "water_readings",
            "count": 0,
            "latest_date": None,
            "rates": [],
            "statistics": consumption_stats([]),
            "anomaly": {"insufficient_data": True},
        }
    with SessionLocal() as session:
        query = select(Reading).where(Reading.type == "water", Reading.household_id == household_id)
        rows = session.scalars(query.order_by(Reading.reading_date)).all()
    rates = [row.consumption / row.period_days for row in rows]
    anomaly = detect_anomaly(rates, rates[-1]) if rates else {"insufficient_data": True}
    return {
        "type": "water_readings",
        "count": len(rows),
        "latest_date": rows[-1].reading_date.isoformat() if rows else None,
        "rates": rates,
        "statistics": consumption_stats(rates),
        "anomaly": anomaly,
    }


def maintenance_statuses(household_id: str | None = None) -> dict:
    today = clock.now().date()
    if not household_id:
        return {
            "type": "maintenance_statuses",
            "today": today.isoformat(),
            "items": [],
        }
    with SessionLocal() as session:
        query = select(Appliance).where(Appliance.household_id == household_id).order_by(Appliance.name)
        rows = session.scalars(query).all()
    return {
        "type": "maintenance_statuses",
        "today": today.isoformat(),
        "items": [
            {
                "appliance": row.name,
                "warranty": warranty_status(row.warranty_end, today, get_settings().warranty_warn_days),
                "maintenance": maintenance_status(
                    row.last_service_date, row.service_interval_days, today
                ),
            }
            for row in rows
        ],
    }


def inventory_levels(household_id: str | None = None) -> dict:
    if not household_id:
        return {
            "type": "inventory_levels",
            "items": [],
        }
    with SessionLocal() as session:
        query = select(InventoryItem).where(InventoryItem.household_id == household_id).order_by(InventoryItem.name)
        rows = session.scalars(query).all()
    return {
        "type": "inventory_levels",
        "items": [
            {
                "item": row.name,
                "quantity": row.quantity,
                "unit": row.unit,
                "reorder_threshold": row.reorder_threshold,
                "low": row.quantity <= row.reorder_threshold,
            }
            for row in rows
        ],
    }


TOOLSETS = {
    "energy": (energy_readings,),
    "water": (water_readings,),
    "maintenance": (maintenance_statuses,),
    "inventory": (inventory_levels,),
}
