from __future__ import annotations

import csv
import io
from typing import Iterable

from app.models.schemas import TransactionInput

REQUIRED_COLUMNS = {"date", "description", "amount"}


def parse_transactions_csv(raw_bytes: bytes) -> list[TransactionInput]:
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV file has no header row.")

    header_map = {name.strip().lower(): name for name in reader.fieldnames if name}
    missing = REQUIRED_COLUMNS - set(header_map.keys())
    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(sorted(missing))
        )

    rows: list[TransactionInput] = []
    for idx, row in enumerate(reader, start=2):
        try:
            date_value = (row.get(header_map["date"]) or "").strip()
            description = (row.get(header_map["description"]) or "").strip()
            amount_raw = (row.get(header_map["amount"]) or "").strip().replace(",", ""
            )
            merchant_column = header_map.get("merchant")
            merchant = (
                (row.get(merchant_column) or "").strip() if merchant_column else None
            )

            if not date_value or not description or not amount_raw:
                raise ValueError("Required field is empty")

            rows.append(
                TransactionInput(
                    txn_date=date_value,
                    description=description,
                    amount=float(amount_raw),
                    merchant=merchant or None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Invalid row at line {idx}: {exc}") from exc

    if not rows:
        raise ValueError("CSV has no data rows.")

    return rows
