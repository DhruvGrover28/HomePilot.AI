from __future__ import annotations

from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import Appliance, InventoryItem, Reading, UtilityBill
from app.db.session import SessionLocal
from app.domain import consumption_stats, detect_anomaly, maintenance_status, warranty_status


def utility_bills_summary(utility_type: str, household_id: str | None = None) -> dict:
    if not household_id:
        return {"utility_type": utility_type, "count": 0, "bills": []}
    with SessionLocal() as session:
        bills = session.scalars(
            select(UtilityBill).where(
                UtilityBill.utility_type == utility_type,
                UtilityBill.household_id == household_id,
            ).order_by(UtilityBill.period_end.desc()).limit(5)
        ).all()
        return {
            "utility_type": utility_type,
            "count": len(bills),
            "total_spend": sum(b.total_amount for b in bills if b.total_amount is not None),
            "latest_bill": {
                "period": f"{bills[0].period_start} to {bills[0].period_end}",
                "consumption": bills[0].consumption,
                "amount": bills[0].total_amount,
            } if bills else None,
        }


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
    bill_summary = utility_bills_summary("electricity", household_id)
    return {
        "type": "energy_readings",
        "count": len(rows),
        "latest_date": rows[-1].reading_date.isoformat() if rows else None,
        "rates": rates,
        "statistics": consumption_stats(rates),
        "anomaly": anomaly,
        "bills_summary": bill_summary,
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
    bill_summary = utility_bills_summary("water", household_id)
    return {
        "type": "water_readings",
        "count": len(rows),
        "latest_date": rows[-1].reading_date.isoformat() if rows else None,
        "rates": rates,
        "statistics": consumption_stats(rates),
        "anomaly": anomaly,
        "bills_summary": bill_summary,
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
