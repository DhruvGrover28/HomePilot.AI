from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile

from app.schemas import BillConfirmRequest, BillExtractionResult
from app.services.auth import get_current_household
from app.services.bill_service import (
    analyze_utility_bills,
    confirm_and_persist_bill,
    extract_bill_data,
    get_bill_by_id,
    list_utility_bills,
    validate_bill_file,
)

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.post("/extract", response_model=BillExtractionResult)
async def extract_bill(
    file: UploadFile = File(...),
    utility_type: str = Form(...),
    household=Depends(get_current_household),
) -> BillExtractionResult:
    if not file.filename:
        raise HTTPException(400, "Filename is required.")
    if utility_type not in {"electricity", "water"}:
        raise HTTPException(422, "utility_type must be 'electricity' or 'water'.")

    content = await file.read()
    try:
        validate_bill_file(content, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        return extract_bill_data(
            content,
            file.filename,
            utility_type,
            household_id=household.id,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/confirm")
def confirm_bill(
    payload: BillConfirmRequest,
    household=Depends(get_current_household),
) -> dict[str, Any]:
    try:
        return confirm_and_persist_bill(payload, household_id=household.id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("")
def list_bills(
    utility_type: str | None = None,
    household=Depends(get_current_household),
) -> list[dict[str, Any]]:
    return list_utility_bills(household_id=household.id, utility_type=utility_type)


@router.get("/analysis")
def get_bill_analysis(
    utility_type: str = Query(..., description="electricity or water"),
    household=Depends(get_current_household),
) -> dict[str, Any]:
    if utility_type not in {"electricity", "water"}:
        raise HTTPException(422, "utility_type must be 'electricity' or 'water'.")
    return analyze_utility_bills(household_id=household.id, utility_type=utility_type)


@router.get("/{bill_id}")
def read_bill(
    bill_id: str,
    household=Depends(get_current_household),
) -> dict[str, Any]:
    bill = get_bill_by_id(bill_id, household_id=household.id)
    if bill is None:
        raise HTTPException(404, "Bill not found.")
    return {
        "id": bill.id,
        "utility_type": bill.utility_type,
        "provider_name": bill.provider_name,
        "account_number": bill.account_number,
        "bill_number": bill.bill_number,
        "bill_date": bill.bill_date.isoformat() if bill.bill_date else None,
        "due_date": bill.due_date.isoformat() if bill.due_date else None,
        "period_start": bill.period_start.isoformat() if bill.period_start else None,
        "period_end": bill.period_end.isoformat() if bill.period_end else None,
        "period_days": bill.period_days,
        "previous_reading": bill.previous_reading,
        "current_reading": bill.current_reading,
        "consumption": bill.consumption,
        "consumption_unit": bill.consumption_unit,
        "total_amount": bill.total_amount,
        "currency": bill.currency,
        "fixed_charges": bill.fixed_charges,
        "variable_charges": bill.variable_charges,
        "taxes": bill.taxes,
        "other_charges": bill.other_charges,
        "source_filename": bill.source_filename,
        "status": bill.status,
        "created_at": bill.created_at.isoformat(),
    }


@router.get("/{bill_id}/csv")
def download_bill_csv(
    bill_id: str,
    household=Depends(get_current_household),
) -> Response:
    bill = get_bill_by_id(bill_id, household_id=household.id)
    if bill is None:
        raise HTTPException(404, "Bill not found.")
    return Response(
        content=bill.csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="bill-{bill.utility_type}-{bill.id}.csv"'
        },
    )
