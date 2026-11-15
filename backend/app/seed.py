from datetime import date, timedelta
from random import Random

from sqlalchemy import select

from app import clock
from app.db.models import Appliance, InventoryItem, InventoryLog, Reading
from app.db.session import SessionLocal


def seed_demo(household_id: str | None = None) -> dict[str, int]:
    with SessionLocal() as session:
        check_query = select(Reading.id)
        if household_id is not None:
            check_query = check_query.where(Reading.household_id == household_id)
        else:
            check_query = check_query.where(Reading.household_id.is_(None))
        if session.scalar(check_query.limit(1)):
            return {"created": 0}
        rng = Random(7)
        today = clock.now().date()
        created = 0
        for days_ago in range(90, 0, -7):
            reading_date = today - timedelta(days=days_ago)
            for kind, unit, base in (("electricity", "kWh", 42), ("water", "litres", 950)):
                value = max(0.1, base + rng.uniform(-base * 0.1, base * 0.1))
                session.add(Reading(
                    household_id=household_id,
                    type=kind, reading_date=reading_date, period_days=7,
                    consumption=value, unit=unit, source="seed", is_simulated=True,
                    created_at=clock.now(),
                ))
                created += 1
        appliances = [
            ("Air conditioner", "cooling", 1800, today - timedelta(days=500), today + timedelta(days=365)),
            ("Refrigerator", "kitchen", 250, today - timedelta(days=300), today + timedelta(days=20)),
            ("Washing machine", "laundry", 600, today - timedelta(days=240), today + timedelta(days=120)),
            ("Water heater", "water", 1500, today - timedelta(days=600), today + timedelta(days=500)),
            ("Dishwasher", "kitchen", 1200, today - timedelta(days=200), today + timedelta(days=400)),
        ]
        for name, category, watts, purchase, warranty in appliances:
            session.add(Appliance(
                household_id=household_id,
                name=name, category=category, rated_watts=watts, purchase_date=purchase,
                warranty_end=warranty, last_service_date=today - timedelta(days=450),
                service_interval_days=365, is_simulated=True, created_at=clock.now(),
            ))
            created += 1
        for index, name in enumerate(["Milk", "Rice", "Coffee", "Detergent", "Toilet paper", "Soap", "Pasta", "Cereal"]):
            item = InventoryItem(household_id=household_id, name=name, quantity=5 + index, unit="unit", reorder_threshold=2, is_simulated=True, created_at=clock.now())
            session.add(item)
            session.flush()
            for history_days, quantity in ((14, 8 + index), (7, 6 + index), (0, 5 + index)):
                session.add(InventoryLog(
                    household_id=household_id,
                    item_id=item.id, quantity=quantity, logged_at=clock.now() - timedelta(days=history_days),
                    source="seed", is_simulated=True, created_at=clock.now(),
                ))
            created += 1
        session.commit()
        return {"created": created}
