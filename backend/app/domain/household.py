from datetime import date, datetime, timedelta
from statistics import mean


def depletion_estimate(log_entries: list[dict]) -> dict:
    ordered = sorted(log_entries, key=lambda entry: entry["logged_at"])
    intervals: list[float] = []
    for previous, current in zip(ordered, ordered[1:]):
        days = (current["logged_at"] - previous["logged_at"]).total_seconds() / 86400
        decrease = previous["quantity"] - current["quantity"]
        if days > 0 and decrease > 0:
            intervals.append(decrease / days)
    if not intervals or not ordered:
        return {"average_daily_use": 0.0, "days_remaining": None, "run_out_date": None, "confidence": "low"}
    daily_use = mean(intervals)
    remaining = ordered[-1]["quantity"] / daily_use if daily_use else None
    return {
        "average_daily_use": daily_use,
        "days_remaining": remaining,
        "run_out_date": ordered[-1]["logged_at"] + timedelta(days=remaining) if remaining is not None else None,
        "confidence": "low" if len(intervals) < 3 else "medium",
    }


def warranty_status(warranty_end: date | None, today: date, warn_days: int) -> dict:
    if warranty_end is None:
        return {"status": "unknown", "days_remaining": None}
    days = (warranty_end - today).days
    status = "expired" if days < 0 else "expiring_soon" if days <= warn_days else "active"
    return {"status": status, "days_remaining": days}


def maintenance_status(last_service: date | None, interval_days: int | None, today: date) -> dict:
    if last_service is None or interval_days is None:
        return {"status": "unknown", "days_overdue": None}
    due = last_service + timedelta(days=interval_days)
    days_overdue = (today - due).days
    status = "overdue" if days_overdue > 0 else "due_soon" if days_overdue >= -30 else "ok"
    return {"status": status, "days_overdue": max(0, days_overdue)}


def estimate_carbon_kg(kwh: float, emission_factor: float) -> dict[str, float | str]:
    return {"value": kwh * emission_factor, "label": "estimate"}


def estimate_cost_impact(extra_consumption: float, unit_price: float | None) -> dict:
    if unit_price is None:
        return {"status": "unavailable", "value": None}
    return {"status": "available", "value": extra_consumption * unit_price}


def priority_score(severity: float, confidence: float, urgency: float, corroboration: float, ease: float) -> float:
    return round(max(0.0, min(100.0, (severity * 0.35 + urgency * 0.25 + confidence * 0.2 + corroboration * 0.1 + ease * 0.1) * 100)), 2)


def fingerprint(category: str, subject: str, severity: str) -> str:
    return f"{category}:{subject}:{severity}"
