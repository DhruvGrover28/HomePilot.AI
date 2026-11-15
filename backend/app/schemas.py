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


class InventoryDetectedItem(BaseModel):
    name: str = Field(min_length=1)
    category: str = "general"
    estimated_quantity: float = Field(ge=0)
    unit: str = "pcs"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    brand: str | None = None
    notes: str | None = None
    matched_item_id: int | None = None
    existing_quantity: float | None = None


class InventoryScanResponse(BaseModel):
    detected_items: list[InventoryDetectedItem]
    image_summary: str = ""
    warnings: list[str] = Field(default_factory=list)


class InventoryReconciliationItem(BaseModel):
    action: Literal["add", "replace", "new", "ignore"]
    item_id: int | None = None
    name: str = Field(min_length=1)
    quantity: float = Field(ge=0)
    unit: str = Field(min_length=1)
    category: str = "general"
    reorder_threshold: float = Field(default=1.0, ge=0)


class InventoryReconciliationRequest(BaseModel):
    items: list[InventoryReconciliationItem]


class InventoryReconciliationResponse(BaseModel):
    updated_items: list[dict]
    created_items: list[dict]
    ignored_count: int


class BillExtractionResult(BaseModel):
    utility_type: Literal["electricity", "water"]
    provider_name: str | None = None
    account_number: str | None = None
    bill_number: str | None = None
    bill_date: date | None = None
    due_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_days: int = Field(default=30, ge=1)
    previous_reading: float | None = Field(default=None, ge=0)
    current_reading: float | None = Field(default=None, ge=0)
    consumption: float = Field(ge=0)
    consumption_unit: str = "kWh"
    total_amount: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    fixed_charges: float | None = Field(default=None, ge=0)
    variable_charges: float | None = Field(default=None, ge=0)
    taxes: float | None = Field(default=None, ge=0)
    other_charges: float | None = Field(default=None, ge=0)
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    source_filename: str = ""


class BillConfirmRequest(BaseModel):
    utility_type: Literal["electricity", "water"]
    provider_name: str | None = None
    account_number: str | None = None
    bill_number: str | None = None
    bill_date: date | None = None
    due_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_days: int = Field(default=30, ge=1)
    previous_reading: float | None = Field(default=None, ge=0)
    current_reading: float | None = Field(default=None, ge=0)
    consumption: float = Field(ge=0)
    consumption_unit: str = "kWh"
    total_amount: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    fixed_charges: float | None = Field(default=None, ge=0)
    variable_charges: float | None = Field(default=None, ge=0)
    taxes: float | None = Field(default=None, ge=0)
    other_charges: float | None = Field(default=None, ge=0)
    source_filename: str = "uploaded_bill"
    sync_reading: bool = True
