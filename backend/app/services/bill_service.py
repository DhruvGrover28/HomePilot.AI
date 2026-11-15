from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import Reading, UtilityBill
from app.db.session import SessionLocal
from app.schemas import BillConfirmRequest, BillExtractionResult
from app.services.monitoring_runtime import monitoring_runtime

MAX_BILL_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_BILL_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

CSV_HEADERS = [
    "bill_id",
    "household_id",
    "utility_type",
    "provider_name",
    "account_number",
    "bill_number",
    "bill_date",
    "due_date",
    "period_start",
    "period_end",
    "period_days",
    "previous_reading",
    "current_reading",
    "consumption",
    "consumption_unit",
    "total_amount",
    "currency",
    "fixed_charges",
    "variable_charges",
    "taxes",
    "other_charges",
    "source_filename",
    "created_at",
]


def validate_bill_file(file_bytes: bytes, filename: str) -> str:
    """Validates bill file size, extension, and header bytes. Returns MIME type."""
    if len(file_bytes) == 0:
        raise ValueError("Uploaded bill file is empty.")
    if len(file_bytes) > MAX_BILL_FILE_SIZE:
        raise ValueError("Bill file size exceeds the 10 MB limit.")

    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_BILL_EXTENSIONS):
        raise ValueError("Unsupported file format. Allowed formats: PDF, JPG, JPEG, PNG, WEBP.")

    if lower.endswith(".pdf"):
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError("Corrupt or invalid PDF file header.")
        return "application/pdf"

    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[:16]:
        return "image/webp"

    raise ValueError("Corrupt or unsupported file content.")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text from PDF pages using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text).strip()
    except Exception as exc:
        raise ValueError(f"Failed to read PDF document: {exc}") from exc


def extract_bill_data(
    file_bytes: bytes,
    filename: str,
    utility_type: str,
    *,
    household_id: str | None = None,
) -> BillExtractionResult:
    """Extracts and normalizes bill metadata from PDF or image using OCR/LLM."""
    if utility_type not in {"electricity", "water"}:
        raise ValueError("utility_type must be 'electricity' or 'water'.")

    mime_type = validate_bill_file(file_bytes, filename)
    settings = get_settings()

    # In mock mode, generate realistic deterministic extraction
    if settings.llm_mode == "mock":
        today = clock.now().date()
        if utility_type == "electricity":
            return BillExtractionResult(
                utility_type="electricity",
                provider_name="Metropolitan Electric Co.",
                account_number="ELEC-849204",
                bill_number=f"INV-{today.strftime('%Y%m')}-4812",
                bill_date=today,
                due_date=date(today.year, today.month, 28) if today.day <= 28 else date(today.year, today.month, 30),
                period_start=date(today.year, max(1, today.month - 1), 1),
                period_end=date(today.year, today.month, 1),
                period_days=30,
                previous_reading=14250.0,
                current_reading=14680.0,
                consumption=430.0,
                consumption_unit="kWh",
                total_amount=94.60,
                currency="USD",
                fixed_charges=15.00,
                variable_charges=73.10,
                taxes=6.50,
                other_charges=0.0,
                confidence_score=0.92,
                warnings=[],
                source_filename=filename,
            )
        else:  # water
            return BillExtractionResult(
                utility_type="water",
                provider_name="City Water & Sewage Authority",
                account_number="WTR-301928",
                bill_number=f"WTR-{today.strftime('%Y%m')}-1940",
                bill_date=today,
                due_date=date(today.year, today.month, 25) if today.day <= 25 else date(today.year, today.month, 28),
                period_start=date(today.year, max(1, today.month - 1), 1),
                period_end=date(today.year, today.month, 1),
                period_days=30,
                previous_reading=820.0,
                current_reading=838.0,
                consumption=18000.0,
                consumption_unit="litres",
                total_amount=52.40,
                currency="USD",
                fixed_charges=12.00,
                variable_charges=36.00,
                taxes=4.40,
                other_charges=0.0,
                confidence_score=0.90,
                warnings=[],
                source_filename=filename,
            )

    # Live extraction with Gemini / LLM
    if not settings.gemini_api_key:
        raise RuntimeError("Live bill extraction requires GEMINI_API_KEY.")

    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model or "gemini-2.5-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
    )

    pdf_text = ""
    if mime_type == "application/pdf":
        pdf_text = extract_text_from_pdf(file_bytes)

    prompt = (
        f"You are a utility bill digitization specialist for HomePilot AI. "
        f"Extract all relevant billing and consumption data for this {utility_type} bill. "
        "Return a JSON object strictly matching this schema:\n"
        "{\n"
        f'  "utility_type": "{utility_type}",\n'
        '  "provider_name": "...",\n'
        '  "account_number": "...",\n'
        '  "bill_number": "...",\n'
        '  "bill_date": "YYYY-MM-DD",\n'
        '  "due_date": "YYYY-MM-DD",\n'
        '  "period_start": "YYYY-MM-DD",\n'
        '  "period_end": "YYYY-MM-DD",\n'
        '  "period_days": 30,\n'
        '  "previous_reading": 1234.0,\n'
        '  "current_reading": 1567.0,\n'
        '  "consumption": 333.0,\n'
        f'  "consumption_unit": "{"kWh" if utility_type == "electricity" else "litres"}",\n'
        '  "total_amount": 75.50,\n'
        '  "currency": "USD",\n'
        '  "fixed_charges": 10.0,\n'
        '  "variable_charges": 60.0,\n'
        '  "taxes": 5.5,\n'
        '  "other_charges": 0.0,\n'
        '  "confidence_score": 0.9,\n'
        '  "warnings": []\n'
        "}\n"
        "Only extract fields clearly present in the bill. Set missing fields to null. "
        "Do not invent values. If previous/current reading is not found, consumption can be extracted directly. "
        "Return ONLY the valid JSON object without markdown or formatting fences."
    )

    if pdf_text:
        # Pass extracted PDF text directly to LLM
        prompt_with_text = f"{prompt}\n\nDOCUMENT TEXT:\n{pdf_text[:12000]}"
        response = llm.invoke(prompt_with_text)
    else:
        # Multimodal image / scanned bill
        import base64
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:{mime_type};base64,{b64}"},
            ]
        )
        response = llm.invoke([message])

    content = response.content
    if isinstance(content, list):
        content = "".join(str(p) for p in content)
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())

    try:
        data = json.loads(content)
        data["source_filename"] = filename
        data["utility_type"] = utility_type
        return BillExtractionResult.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Failed to parse bill extraction result: {exc}") from exc


def generate_bill_csv(bill_dict: dict[str, Any]) -> str:
    """Generates standardized RFC 4180 CSV representation of a utility bill."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CSV_HEADERS)
    writer.writerow(
        [
            bill_dict.get("id", ""),
            bill_dict.get("household_id", ""),
            bill_dict.get("utility_type", ""),
            bill_dict.get("provider_name", "") or "",
            bill_dict.get("account_number", "") or "",
            bill_dict.get("bill_number", "") or "",
            bill_dict.get("bill_date", "") or "",
            bill_dict.get("due_date", "") or "",
            bill_dict.get("period_start", "") or "",
            bill_dict.get("period_end", "") or "",
            bill_dict.get("period_days", 30),
            bill_dict.get("previous_reading", "") if bill_dict.get("previous_reading") is not None else "",
            bill_dict.get("current_reading", "") if bill_dict.get("current_reading") is not None else "",
            bill_dict.get("consumption", 0.0),
            bill_dict.get("consumption_unit", ""),
            bill_dict.get("total_amount", "") if bill_dict.get("total_amount") is not None else "",
            bill_dict.get("currency", "USD"),
            bill_dict.get("fixed_charges", "") if bill_dict.get("fixed_charges") is not None else "",
            bill_dict.get("variable_charges", "") if bill_dict.get("variable_charges") is not None else "",
            bill_dict.get("taxes", "") if bill_dict.get("taxes") is not None else "",
            bill_dict.get("other_charges", "") if bill_dict.get("other_charges") is not None else "",
            bill_dict.get("source_filename", "") or "",
            bill_dict.get("created_at", "") or "",
        ]
    )
    return output.getvalue()


def confirm_and_persist_bill(
    payload: BillConfirmRequest,
    *,
    household_id: str,
) -> dict[str, Any]:
    """Persists confirmed bill, generates CSV, and synchronizes Reading record."""
    with SessionLocal() as session:
        # Check for duplicates: same household, same utility type, overlapping period
        if payload.period_start and payload.period_end:
            existing_duplicate = session.scalar(
                select(UtilityBill).where(
                    UtilityBill.household_id == household_id,
                    UtilityBill.utility_type == payload.utility_type,
                    UtilityBill.period_start == payload.period_start,
                    UtilityBill.period_end == payload.period_end,
                )
            )
            if existing_duplicate:
                raise ValueError(
                    f"A {payload.utility_type} bill for period {payload.period_start} to {payload.period_end} has already been imported."
                )

        bill_id = str(uuid4())
        now = clock.now()

        bill_data = {
            "id": bill_id,
            "household_id": household_id,
            "utility_type": payload.utility_type,
            "provider_name": payload.provider_name,
            "account_number": payload.account_number,
            "bill_number": payload.bill_number,
            "bill_date": payload.bill_date.isoformat() if payload.bill_date else None,
            "due_date": payload.due_date.isoformat() if payload.due_date else None,
            "period_start": payload.period_start.isoformat() if payload.period_start else None,
            "period_end": payload.period_end.isoformat() if payload.period_end else None,
            "period_days": payload.period_days,
            "previous_reading": payload.previous_reading,
            "current_reading": payload.current_reading,
            "consumption": payload.consumption,
            "consumption_unit": payload.consumption_unit,
            "total_amount": payload.total_amount,
            "currency": payload.currency,
            "fixed_charges": payload.fixed_charges,
            "variable_charges": payload.variable_charges,
            "taxes": payload.taxes,
            "other_charges": payload.other_charges,
            "source_filename": payload.source_filename,
            "created_at": now.isoformat(),
        }

        csv_content = generate_bill_csv(bill_data)

        bill_row = UtilityBill(
            id=bill_id,
            household_id=household_id,
            utility_type=payload.utility_type,
            provider_name=payload.provider_name,
            account_number=payload.account_number,
            bill_number=payload.bill_number,
            bill_date=payload.bill_date,
            due_date=payload.due_date,
            period_start=payload.period_start,
            period_end=payload.period_end,
            period_days=payload.period_days,
            previous_reading=payload.previous_reading,
            current_reading=payload.current_reading,
            consumption=payload.consumption,
            consumption_unit=payload.consumption_unit,
            total_amount=payload.total_amount,
            currency=payload.currency,
            fixed_charges=payload.fixed_charges,
            variable_charges=payload.variable_charges,
            taxes=payload.taxes,
            other_charges=payload.other_charges,
            csv_content=csv_content,
            raw_data_json=json.dumps(bill_data),
            source_filename=payload.source_filename,
            status="confirmed",
            created_at=now,
        )
        session.add(bill_row)

        # Synchronize Reading record if requested
        if payload.sync_reading:
            reading_date = payload.period_end or payload.bill_date or now.date()
            reading_type = "electricity" if payload.utility_type == "electricity" else "water"
            reading_unit = "kWh" if payload.utility_type == "electricity" else "litres"

            reading_row = Reading(
                household_id=household_id,
                type=reading_type,
                reading_date=reading_date,
                meter_value=payload.current_reading,
                period_days=payload.period_days,
                consumption=payload.consumption,
                unit=reading_unit,
                amount=payload.total_amount,
                source="bill",
                is_simulated=False,
                created_at=now,
            )
            session.add(reading_row)

        session.commit()

    monitoring_runtime.trigger_event(
        ["energy" if payload.utility_type == "electricity" else "water"],
        household_id,
    )
    return bill_data


def list_utility_bills(
    *,
    household_id: str,
    utility_type: str | None = None,
) -> list[dict[str, Any]]:
    """Lists confirmed utility bills for the household."""
    with SessionLocal() as session:
        query = select(UtilityBill).where(UtilityBill.household_id == household_id)
        if utility_type:
            query = query.where(UtilityBill.utility_type == utility_type)
        bills = session.scalars(query.order_by(UtilityBill.period_end.desc().nullslast(), UtilityBill.created_at.desc())).all()
        return [
            {
                "id": b.id,
                "utility_type": b.utility_type,
                "provider_name": b.provider_name,
                "account_number": b.account_number,
                "bill_number": b.bill_number,
                "bill_date": b.bill_date.isoformat() if b.bill_date else None,
                "due_date": b.due_date.isoformat() if b.due_date else None,
                "period_start": b.period_start.isoformat() if b.period_start else None,
                "period_end": b.period_end.isoformat() if b.period_end else None,
                "period_days": b.period_days,
                "previous_reading": b.previous_reading,
                "current_reading": b.current_reading,
                "consumption": b.consumption,
                "consumption_unit": b.consumption_unit,
                "total_amount": b.total_amount,
                "currency": b.currency,
                "fixed_charges": b.fixed_charges,
                "variable_charges": b.variable_charges,
                "taxes": b.taxes,
                "other_charges": b.other_charges,
                "source_filename": b.source_filename,
                "status": b.status,
                "created_at": b.created_at.isoformat(),
            }
            for b in bills
        ]


def get_bill_by_id(bill_id: str, *, household_id: str) -> UtilityBill | None:
    """Fetches a single utility bill ensuring household isolation."""
    with SessionLocal() as session:
        return session.scalar(
            select(UtilityBill).where(
                UtilityBill.id == bill_id,
                UtilityBill.household_id == household_id,
            )
        )


def analyze_utility_bills(
    *,
    household_id: str,
    utility_type: str,
) -> dict[str, Any]:
    """Computes trends, cost breakdowns, and anomalies across confirmed bills."""
    bills = list_utility_bills(household_id=household_id, utility_type=utility_type)
    total_count = len(bills)

    if total_count == 0:
        return {
            "utility_type": utility_type,
            "total_bills": 0,
            "message": "No confirmed bills available for analysis.",
            "average_consumption": 0.0,
            "average_daily_consumption": 0.0,
            "consumption_trend_pct": None,
            "total_spend": 0.0,
            "average_bill_amount": 0.0,
            "cost_per_unit": None,
            "anomalies": [],
            "warnings": ["Upload and confirm utility bills to generate historical trend analytics."],
            "history": [],
        }

    # Chronological sort for historical trend analysis
    sorted_bills = sorted(
        bills,
        key=lambda b: (b["period_end"] or b["created_at"], b["id"]),
    )

    consumptions = [b["consumption"] for b in sorted_bills]
    daily_rates = [
        b["consumption"] / max(1, b["period_days"])
        for b in sorted_bills
    ]
    amounts = [b["total_amount"] for b in sorted_bills if b["total_amount"] is not None]

    avg_consumption = sum(consumptions) / total_count
    avg_daily = sum(daily_rates) / total_count
    total_spend = sum(amounts)
    avg_amount = (total_spend / len(amounts)) if amounts else 0.0

    cost_per_unit = (total_spend / sum(consumptions)) if sum(consumptions) > 0 and amounts else None

    # Period-over-period consumption change between latest two bills
    pop_change_pct = None
    if total_count >= 2:
        prev_rate = daily_rates[-2]
        latest_rate = daily_rates[-1]
        if prev_rate > 0:
            pop_change_pct = round(((latest_rate - prev_rate) / prev_rate) * 100, 1)

    # Anomaly detection: daily consumption rate > 1.4x average (if at least 3 bills)
    anomalies: list[dict[str, Any]] = []
    if total_count >= 3:
        for idx, (bill, rate) in enumerate(zip(sorted_bills, daily_rates)):
            if rate > (avg_daily * 1.4):
                anomalies.append(
                    {
                        "bill_id": bill["id"],
                        "period": f"{bill['period_start']} to {bill['period_end']}",
                        "daily_rate": round(rate, 2),
                        "baseline_daily_rate": round(avg_daily, 2),
                        "spike_pct": round(((rate - avg_daily) / avg_daily) * 100, 1),
                        "severity": "high" if rate > (avg_daily * 1.7) else "medium",
                    }
                )

    warnings: list[str] = []
    if total_count == 1:
        warnings.append(
            "Only 1 bill is recorded. A single bill represents a single snapshot and cannot establish historical consumption trends."
        )
    elif total_count < 3:
        warnings.append(
            "Only 2 bills are recorded. Additional billing periods are recommended to establish a robust consumption baseline."
        )

    return {
        "utility_type": utility_type,
        "total_bills": total_count,
        "average_consumption": round(avg_consumption, 2),
        "average_daily_consumption": round(avg_daily, 2),
        "consumption_trend_pct": pop_change_pct,
        "total_spend": round(total_spend, 2),
        "average_bill_amount": round(avg_amount, 2),
        "cost_per_unit": round(cost_per_unit, 4) if cost_per_unit is not None else None,
        "unit": "kWh" if utility_type == "electricity" else "litres",
        "currency": sorted_bills[0]["currency"] if sorted_bills else "USD",
        "anomalies": anomalies,
        "warnings": warnings,
        "history": [
            {
                "id": b["id"],
                "period": f"{b['period_start'] or ''} - {b['period_end'] or ''}",
                "period_end": b["period_end"],
                "consumption": b["consumption"],
                "daily_rate": round(b["consumption"] / max(1, b["period_days"]), 2),
                "amount": b["total_amount"],
                "provider": b["provider_name"],
            }
            for b in sorted_bills
        ],
    }
