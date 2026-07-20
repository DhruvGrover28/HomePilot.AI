from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    txn_date: str = Field(..., description="Date as provided in CSV")
    description: str = Field(..., min_length=1)
    amount: float
    merchant: str | None = None


class TransactionRecord(BaseModel):
    id: int
    upload_id: str
    txn_date: str
    description: str
    merchant: str | None
    amount: float
    category: str
    anomaly_type: str | None
    anomaly_reason: str | None
    confidence: float | None
    created_at: datetime


class CategorizationItem(BaseModel):
    row_index: int = Field(..., ge=0)
    category: Literal[
        "Housing",
        "Utilities",
        "Groceries",
        "Transportation",
        "Healthcare",
        "Insurance",
        "Entertainment",
        "Shopping",
        "Dining",
        "Income",
        "Education",
        "Other",
    ]
    confidence: float = Field(..., ge=0, le=1)


class CategorizationResult(BaseModel):
    items: list[CategorizationItem]


class UploadResponseItem(BaseModel):
    txn_date: str
    description: str
    merchant: str | None
    amount: float
    category: str
    anomaly_type: str | None
    anomaly_reason: str | None
    confidence: float | None


class UploadResponse(BaseModel):
    upload_id: str
    transactions: list[UploadResponseItem]
    anomalies_count: int
