import csv
import io
from datetime import date

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app import clock
from app.db.models import Appliance, InventoryItem, InventoryLog, Reading, ShoppingListItem, Task
from app.db.session import SessionLocal
from app.domain import consumption_stats
from app.schemas import ApplianceCreate, InventoryCreate, InventoryUpdate, ReadingCreate, ShoppingCreate, TaskCreate
from app.services.monitoring_runtime import monitoring_runtime

router = APIRouter(prefix="/api", tags=["household"])


def _read(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.get("/readings")
def list_readings(type: str | None = None) -> list[dict]:
    with SessionLocal() as session:
        query = select(Reading).order_by(Reading.reading_date)
        if type:
            query = query.where(Reading.type == type)
        return [_read(row) for row in session.scalars(query).all()]


@router.post("/readings")
def create_reading(payload: ReadingCreate) -> dict:
    with SessionLocal() as session:
        previous = session.scalar(select(Reading).where(Reading.type == payload.type).order_by(Reading.reading_date.desc()).limit(1))
        if payload.meter_value is not None and previous and previous.meter_value is not None and payload.meter_value < previous.meter_value:
            raise HTTPException(422, "Meter value cannot be lower than the previous reading.")
        row = Reading(**payload.model_dump(), created_at=clock.now())
        session.add(row)
        session.commit()
        session.refresh(row)
        monitoring_runtime.trigger_event(["energy" if payload.type == "electricity" else "water"])
        return _read(row)


@router.patch("/readings/{reading_id}")
def update_reading(reading_id: int, payload: ReadingCreate) -> dict:
    with SessionLocal() as session:
        row = session.get(Reading, reading_id)
        if row is None:
            raise HTTPException(404, "Reading not found.")
        previous = session.scalar(
            select(Reading)
            .where(Reading.type == payload.type, Reading.id != reading_id)
            .order_by(Reading.reading_date.desc())
            .limit(1)
        )
        if payload.meter_value is not None and previous and previous.meter_value is not None and payload.meter_value < previous.meter_value:
            raise HTTPException(422, "Meter value cannot be lower than the previous reading.")
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["energy" if payload.type == "electricity" else "water"])
        return _read(row)


@router.delete("/readings/{reading_id}", status_code=204)
def delete_reading(reading_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Reading, reading_id)
        if row is None:
            raise HTTPException(404, "Reading not found.")
        domain = "energy" if row.type == "electricity" else "water"
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event([domain])


@router.post("/readings/import")
async def import_readings(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported.")
    reader = csv.DictReader(io.StringIO((await file.read()).decode("utf-8-sig")))
    required = {"type", "reading_date", "meter_value", "consumption", "period_days"}
    if not reader.fieldnames or not required.issubset({field.strip() for field in reader.fieldnames}):
        raise HTTPException(400, {"errors": ["CSV must include type, reading_date, meter_value, consumption and period_days."]})
    valid: list[ReadingCreate] = []
    errors: list[str] = []
    for line, row in enumerate(reader, 2):
        try:
            kind = row["type"].strip()
            if kind not in {"electricity", "water"}:
                raise ValueError("type must be electricity or water")
            valid.append(ReadingCreate(
                type=kind, reading_date=date.fromisoformat(row["reading_date"].strip()),
                meter_value=float(row["meter_value"]) if row["meter_value"].strip() else None,
                consumption=float(row["consumption"]), period_days=int(row["period_days"]),
                unit="kWh" if kind == "electricity" else "litres", source="manual",
            ))
        except (KeyError, ValueError) as exc:
            errors.append(f"row {line}: {exc}")
    if errors:
        raise HTTPException(422, {"errors": errors})
    with SessionLocal() as session:
        session.add_all([Reading(**item.model_dump(), created_at=clock.now()) for item in valid])
        session.commit()
    monitoring_runtime.trigger_event(sorted({"energy" if item.type == "electricity" else "water" for item in valid}))
    return {"imported": len(valid)}


@router.get("/appliances")
def list_appliances() -> list[dict]:
    with SessionLocal() as session:
        return [_read(row) for row in session.scalars(select(Appliance).order_by(Appliance.name)).all()]


@router.post("/appliances")
def create_appliance(payload: ApplianceCreate) -> dict:
    with SessionLocal() as session:
        row = Appliance(**payload.model_dump(), created_at=clock.now())
        session.add(row); session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"])
        return _read(row)


@router.get("/inventory")
def list_inventory() -> list[dict]:
    with SessionLocal() as session:
        return [_read(row) for row in session.scalars(select(InventoryItem).order_by(InventoryItem.name)).all()]


@router.post("/inventory")
def create_inventory(payload: InventoryCreate) -> dict:
    with SessionLocal() as session:
        row = InventoryItem(**payload.model_dump(), created_at=clock.now())
        session.add(row); session.flush()
        session.add(InventoryLog(item_id=row.id, quantity=row.quantity, logged_at=clock.now(), source="manual", is_simulated=row.is_simulated, created_at=clock.now()))
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["inventory"])
        return _read(row)


@router.patch("/appliances/{appliance_id}")
def update_appliance(appliance_id: int, payload: ApplianceCreate) -> dict:
    with SessionLocal() as session:
        row = session.get(Appliance, appliance_id)
        if row is None:
            raise HTTPException(404, "Appliance not found.")
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"])
        return _read(row)


@router.delete("/appliances/{appliance_id}", status_code=204)
def delete_appliance(appliance_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Appliance, appliance_id)
        if row is None:
            raise HTTPException(404, "Appliance not found.")
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event(["maintenance"])


@router.patch("/inventory/{item_id}")
def update_inventory(item_id: int, payload: InventoryUpdate) -> dict:
    with SessionLocal() as session:
        row = session.get(InventoryItem, item_id)
        if row is None:
            raise HTTPException(404, "Inventory item not found.")
        row.quantity = payload.quantity
        session.add(InventoryLog(item_id=row.id, quantity=row.quantity, logged_at=clock.now(), source=payload.source, is_simulated=row.is_simulated, created_at=clock.now()))
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["inventory"])
        return _read(row)


@router.delete("/inventory/{item_id}", status_code=204)
def delete_inventory(item_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(InventoryItem, item_id)
        if row is None:
            raise HTTPException(404, "Inventory item not found.")
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event(["inventory"])


@router.get("/shopping-list")
def list_shopping() -> list[dict]:
    with SessionLocal() as session:
        return [_read(row) for row in session.scalars(select(ShoppingListItem).order_by(ShoppingListItem.created_at.desc())).all()]


@router.post("/shopping-list")
def create_shopping(payload: ShoppingCreate) -> dict:
    with SessionLocal() as session:
        row = ShoppingListItem(**payload.model_dump(), created_at=clock.now())
        session.add(row); session.commit(); session.refresh(row)
        return _read(row)


@router.patch("/shopping-list/{item_id}")
def update_shopping(item_id: int, payload: ShoppingCreate) -> dict:
    with SessionLocal() as session:
        row = session.get(ShoppingListItem, item_id)
        if row is None:
            raise HTTPException(404, "Shopping-list item not found.")
        row.item_name = payload.item_name
        row.quantity = payload.quantity
        row.unit = payload.unit
        session.commit(); session.refresh(row)
        return _read(row)


@router.delete("/shopping-list/{item_id}", status_code=204)
def delete_shopping(item_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(ShoppingListItem, item_id)
        if row is None:
            raise HTTPException(404, "Shopping-list item not found.")
        session.delete(row)
        session.commit()


@router.get("/tasks")
def list_tasks() -> list[dict]:
    with SessionLocal() as session:
        return [_read(row) for row in session.scalars(select(Task).order_by(Task.due_date)).all()]


@router.post("/tasks")
def create_task(payload: TaskCreate) -> dict:
    with SessionLocal() as session:
        row = Task(**payload.model_dump(), created_at=clock.now())
        session.add(row); session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"])
        return _read(row)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskCreate) -> dict:
    with SessionLocal() as session:
        row = session.get(Task, task_id)
        if row is None:
            raise HTTPException(404, "Task not found.")
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"])
        return _read(row)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Task, task_id)
        if row is None:
            raise HTTPException(404, "Task not found.")
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event(["maintenance"])


@router.get("/dashboard/summary")
def dashboard_summary() -> dict:
    with SessionLocal() as session:
        readings = session.scalars(select(Reading).order_by(Reading.reading_date)).all()
        return {
            "electricity": [_read(row) for row in readings if row.type == "electricity"],
            "water": [_read(row) for row in readings if row.type == "water"],
            "appliances": [_read(row) for row in session.scalars(select(Appliance)).all()],
            "inventory": [_read(row) for row in session.scalars(select(InventoryItem)).all()],
            "tasks_open": len(session.scalars(select(Task).where(Task.status == "open")).all()),
            "stats": consumption_stats([row.consumption / row.period_days for row in readings if row.type == "electricity"]),
        }
