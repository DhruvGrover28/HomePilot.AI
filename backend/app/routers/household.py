import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select

from app import clock
from app.db.models import Appliance, InventoryItem, InventoryLog, Reading, ShoppingListItem, Task
from app.db.session import SessionLocal
from app.domain import consumption_stats
from app.schemas import (
    ApplianceCreate,
    InventoryCreate,
    InventoryReconciliationRequest,
    InventoryReconciliationResponse,
    InventoryScanResponse,
    InventoryUpdate,
    ReadingCreate,
    ShoppingCreate,
    TaskCreate,
)
from app.services.monitoring_runtime import monitoring_runtime
from app.services.auth import get_current_household
from app.services.vision_service import (
    reconcile_inventory_items,
    scan_inventory_image,
    validate_image_bytes,
)

router = APIRouter(prefix="/api", tags=["household"])


def _read(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def _owned(row, household) -> None:
    if row.household_id != household.id:
        raise HTTPException(404, "Resource not found.")


def _scoped(query, model, household):
    return query.where(model.household_id == household.id)


@router.get("/readings")
def list_readings(type: str | None = None, household=Depends(get_current_household)) -> list[dict]:
    with SessionLocal() as session:
        query = _scoped(select(Reading), Reading, household).order_by(Reading.reading_date)
        if type:
            query = query.where(Reading.type == type)
        return [_read(row) for row in session.scalars(query).all()]


@router.post("/readings")
def create_reading(payload: ReadingCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        previous_query = _scoped(
            select(Reading).where(Reading.type == payload.type),
            Reading,
            household,
        )
        previous = session.scalar(previous_query.order_by(Reading.reading_date.desc()).limit(1))
        if payload.meter_value is not None and previous and previous.meter_value is not None and payload.meter_value < previous.meter_value:
            raise HTTPException(422, "Meter value cannot be lower than the previous reading.")
        row = Reading(
            **payload.model_dump(),
            household_id=household.id if household else None,
            created_at=clock.now(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        monitoring_runtime.trigger_event(
            ["energy" if payload.type == "electricity" else "water"],
            household.id if household else None,
        )
        return _read(row)


@router.patch("/readings/{reading_id}")
def update_reading(reading_id: int, payload: ReadingCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = session.get(Reading, reading_id)
        if row is None:
            raise HTTPException(404, "Reading not found.")
        _owned(row, household)
        query = _scoped(
            select(Reading).where(
                Reading.type == payload.type,
                Reading.id != reading_id,
            ),
            Reading,
            household,
        )
        previous = session.scalar(query.order_by(Reading.reading_date.desc()).limit(1))
        if payload.meter_value is not None and previous and previous.meter_value is not None and payload.meter_value < previous.meter_value:
            raise HTTPException(422, "Meter value cannot be lower than the previous reading.")
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(
            ["energy" if payload.type == "electricity" else "water"],
            household.id if household else None,
        )
        return _read(row)


@router.delete("/readings/{reading_id}", status_code=204)
def delete_reading(reading_id: int, household=Depends(get_current_household)) -> None:
    with SessionLocal() as session:
        row = session.get(Reading, reading_id)
        if row is None:
            raise HTTPException(404, "Reading not found.")
        _owned(row, household)
        domain = "energy" if row.type == "electricity" else "water"
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event([domain], household.id if household else None)


@router.post("/readings/import")
async def import_readings(
    file: UploadFile = File(...),
    household=Depends(get_current_household),
) -> dict:
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
        session.add_all(
            [
                Reading(
                    **item.model_dump(),
                    household_id=household.id if household else None,
                    created_at=clock.now(),
                )
                for item in valid
            ]
        )
        session.commit()
    monitoring_runtime.trigger_event(
        sorted({"energy" if item.type == "electricity" else "water" for item in valid}),
        household.id if household else None,
    )
    return {"imported": len(valid)}


@router.get("/appliances")
def list_appliances(household=Depends(get_current_household)) -> list[dict]:
    with SessionLocal() as session:
        query = _scoped(select(Appliance), Appliance, household).order_by(Appliance.name)
        return [_read(row) for row in session.scalars(query).all()]


@router.post("/appliances")
def create_appliance(payload: ApplianceCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = Appliance(
            **payload.model_dump(),
            household_id=household.id if household else None,
            created_at=clock.now(),
        )
        session.add(row); session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"], household.id if household else None)
        return _read(row)


@router.get("/inventory")
def list_inventory(household=Depends(get_current_household)) -> list[dict]:
    with SessionLocal() as session:
        query = _scoped(select(InventoryItem), InventoryItem, household).order_by(InventoryItem.name)
        return [_read(row) for row in session.scalars(query).all()]


@router.post("/inventory")
def create_inventory(payload: InventoryCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = InventoryItem(
            **payload.model_dump(),
            household_id=household.id if household else None,
            created_at=clock.now(),
        )
        session.add(row); session.flush()
        session.add(
            InventoryLog(
                item_id=row.id,
                household_id=household.id if household else None,
                quantity=row.quantity,
                logged_at=clock.now(),
                source="manual",
                is_simulated=row.is_simulated,
                created_at=clock.now(),
            )
        )
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["inventory"], household.id if household else None)
        return _read(row)


@router.patch("/appliances/{appliance_id}")
def update_appliance(appliance_id: int, payload: ApplianceCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = session.get(Appliance, appliance_id)
        if row is None:
            raise HTTPException(404, "Appliance not found.")
        _owned(row, household)
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"], household.id if household else None)
        return _read(row)


@router.delete("/appliances/{appliance_id}", status_code=204)
def delete_appliance(appliance_id: int, household=Depends(get_current_household)) -> None:
    with SessionLocal() as session:
        row = session.get(Appliance, appliance_id)
        if row is None:
            raise HTTPException(404, "Appliance not found.")
        _owned(row, household)
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event(["maintenance"], household.id if household else None)


@router.patch("/inventory/{item_id}")
def update_inventory(item_id: int, payload: InventoryUpdate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = session.get(InventoryItem, item_id)
        if row is None:
            raise HTTPException(404, "Inventory item not found.")
        _owned(row, household)
        row.quantity = payload.quantity
        session.add(
            InventoryLog(
                item_id=row.id,
                household_id=household.id if household else None,
                quantity=row.quantity,
                logged_at=clock.now(),
                source=payload.source,
                is_simulated=row.is_simulated,
                created_at=clock.now(),
            )
        )
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["inventory"], household.id if household else None)
        return _read(row)


@router.delete("/inventory/{item_id}", status_code=204)
def delete_inventory(item_id: int, household=Depends(get_current_household)) -> None:
    with SessionLocal() as session:
        row = session.get(InventoryItem, item_id)
        if row is None:
            raise HTTPException(404, "Inventory item not found.")
        _owned(row, household)
        session.execute(delete(InventoryLog).where(InventoryLog.item_id == item_id))
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event(["inventory"], household.id if household else None)


@router.post("/inventory/scan", response_model=InventoryScanResponse)
async def scan_inventory(
    file: UploadFile = File(...),
    household=Depends(get_current_household),
) -> InventoryScanResponse:
    if not file.filename:
        raise HTTPException(400, "Filename is required.")
    content = await file.read()
    try:
        mime_type = validate_image_bytes(content, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        return scan_inventory_image(content, mime_type, household_id=household.id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/inventory/reconcile", response_model=InventoryReconciliationResponse)
def reconcile_inventory(
    payload: InventoryReconciliationRequest,
    household=Depends(get_current_household),
) -> InventoryReconciliationResponse:
    try:
        return reconcile_inventory_items(payload.items, household_id=household.id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/shopping-list")
def list_shopping(household=Depends(get_current_household)) -> list[dict]:
    with SessionLocal() as session:
        query = _scoped(select(ShoppingListItem), ShoppingListItem, household).order_by(
            ShoppingListItem.created_at.desc()
        )
        return [_read(row) for row in session.scalars(query).all()]


@router.post("/shopping-list")
def create_shopping(payload: ShoppingCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = ShoppingListItem(
            **payload.model_dump(),
            household_id=household.id if household else None,
            created_at=clock.now(),
        )
        session.add(row); session.commit(); session.refresh(row)
        return _read(row)


@router.patch("/shopping-list/{item_id}")
def update_shopping(item_id: int, payload: ShoppingCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = session.get(ShoppingListItem, item_id)
        if row is None:
            raise HTTPException(404, "Shopping-list item not found.")
        _owned(row, household)
        row.item_name = payload.item_name
        row.quantity = payload.quantity
        row.unit = payload.unit
        session.commit(); session.refresh(row)
        return _read(row)


@router.delete("/shopping-list/{item_id}", status_code=204)
def delete_shopping(item_id: int, household=Depends(get_current_household)) -> None:
    with SessionLocal() as session:
        row = session.get(ShoppingListItem, item_id)
        if row is None:
            raise HTTPException(404, "Shopping-list item not found.")
        _owned(row, household)
        session.delete(row)
        session.commit()


@router.get("/tasks")
def list_tasks(household=Depends(get_current_household)) -> list[dict]:
    with SessionLocal() as session:
        query = _scoped(select(Task), Task, household).order_by(Task.due_date)
        return [_read(row) for row in session.scalars(query).all()]


@router.post("/tasks")
def create_task(payload: TaskCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        if payload.appliance_id is not None:
            appliance = session.get(Appliance, payload.appliance_id)
            if appliance is None:
                raise HTTPException(404, "Appliance not found.")
            _owned(appliance, household)
        row = Task(
            **payload.model_dump(),
            household_id=household.id if household else None,
            created_at=clock.now(),
        )
        session.add(row); session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"], household.id if household else None)
        return _read(row)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskCreate, household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        row = session.get(Task, task_id)
        if row is None:
            raise HTTPException(404, "Task not found.")
        _owned(row, household)
        if payload.appliance_id is not None:
            appliance = session.get(Appliance, payload.appliance_id)
            if appliance is None:
                raise HTTPException(404, "Appliance not found.")
            _owned(appliance, household)
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
        session.commit(); session.refresh(row)
        monitoring_runtime.trigger_event(["maintenance"], household.id if household else None)
        return _read(row)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, household=Depends(get_current_household)) -> None:
    with SessionLocal() as session:
        row = session.get(Task, task_id)
        if row is None:
            raise HTTPException(404, "Task not found.")
        _owned(row, household)
        session.delete(row)
        session.commit()
    monitoring_runtime.trigger_event(["maintenance"], household.id if household else None)


@router.get("/dashboard/summary")
def dashboard_summary(household=Depends(get_current_household)) -> dict:
    with SessionLocal() as session:
        readings = session.scalars(
            _scoped(select(Reading), Reading, household).order_by(Reading.reading_date)
        ).all()
        appliances = session.scalars(_scoped(select(Appliance), Appliance, household)).all()
        inventory = session.scalars(_scoped(select(InventoryItem), InventoryItem, household)).all()
        tasks = session.scalars(
            _scoped(select(Task).where(Task.status == "open"), Task, household)
        ).all()
        return {
            "electricity": [_read(row) for row in readings if row.type == "electricity"],
            "water": [_read(row) for row in readings if row.type == "water"],
            "appliances": [_read(row) for row in appliances],
            "inventory": [_read(row) for row in inventory],
            "tasks_open": len(tasks),
            "stats": consumption_stats([row.consumption / row.period_days for row in readings if row.type == "electricity"]),
        }
