from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReadingCreate(BaseModel):
    type: Literal["electricity", "water"]
    reading_date: date
    meter_value: float | None = Field(default=None, ge=0)
    period_days: int = Field(default=1, ge=1)
    consumption: float = Field(ge=0)
    unit: str
    amount: float | None = Field(default=None, ge=0)
    source: Literal["manual", "telegram", "bill", "seed", "demo"] = "manual"
    is_simulated: bool = False


class ApplianceCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    rated_watts: float | None = Field(default=None, ge=0)
    purchase_date: date | None = None
    warranty_end: date | None = None
    last_service_date: date | None = None
    service_interval_days: int | None = Field(default=None, ge=1)
    is_simulated: bool = False


class InventoryCreate(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(ge=0)
    unit: str = Field(min_length=1)
    reorder_threshold: float = Field(ge=0)
    is_simulated: bool = False


class InventoryUpdate(BaseModel):
    quantity: float = Field(ge=0)
    source: str = "manual"


class ShoppingCreate(BaseModel):
    item_name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1)


class TaskCreate(BaseModel):
    appliance_id: int | None = None
    title: str = Field(min_length=1)
    description: str = ""
    due_date: date


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
