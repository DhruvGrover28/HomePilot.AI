from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.agents.expense_agent import run_expense_categorization
from app.db import get_connection
from app.models.schemas import (
    UploadResponse,
    UploadResponseItem,
    TransactionInput,
)
from app.services.csv_parser_service import parse_transactions_csv


def _detect_anomalies(transactions: list[TransactionInput]) -> dict[int, tuple[str, str]]:
    anomalies: dict[int, tuple[str, str]] = {}
    amounts = [abs(txn.amount) for txn in transactions]
    mean_amount = sum(amounts) / len(amounts)
    variance = sum((amount - mean_amount) ** 2 for amount in amounts) / len(amounts)
    std_dev = math.sqrt(variance)
    high_spend_threshold = max(mean_amount + (2 * std_dev), 400.0)

    for idx, txn in enumerate(transactions):
        if abs(txn.amount) >= high_spend_threshold:
            anomalies[idx] = (
                "UNUSUALLY_LARGE",
                f"Amount {txn.amount:.2f} is above threshold {high_spend_threshold:.2f}.",
            )

    seen: defaultdict[tuple[str, float], list[int]] = defaultdict(list)
    for idx, txn in enumerate(transactions):
        key = (txn.description.strip().lower(), round(txn.amount, 2))
        seen[key].append(idx)

    for idx_list in seen.values():
        if len(idx_list) > 1:
            for idx in idx_list:
                anomalies[idx] = (
                    "POTENTIAL_DUPLICATE",
                    "Duplicate description and amount detected in this upload.",
                )

    return anomalies


def process_expense_upload(raw_bytes: bytes) -> UploadResponse:
    parsed_transactions = parse_transactions_csv(raw_bytes)
    categorization = run_expense_categorization(parsed_transactions)
    anomalies = _detect_anomalies(parsed_transactions)

    upload_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    response_items: list[UploadResponseItem] = []
    with get_connection() as connection:
        for idx, txn in enumerate(parsed_transactions):
            categorization_item = categorization.items[idx]
            anomaly = anomalies.get(idx)
            anomaly_type = anomaly[0] if anomaly else None
            anomaly_reason = anomaly[1] if anomaly else None

            connection.execute(
                """
                INSERT INTO transactions (
                    upload_id,
                    txn_date,
                    description,
                    merchant,
                    amount,
                    category,
                    anomaly_type,
                    anomaly_reason,
                    confidence,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    upload_id,
                    txn.txn_date,
                    txn.description,
                    txn.merchant,
                    txn.amount,
                    categorization_item.category,
                    anomaly_type,
                    anomaly_reason,
                    categorization_item.confidence,
                    created_at,
                ),
            )

            response_items.append(
                UploadResponseItem(
                    txn_date=txn.txn_date,
                    description=txn.description,
                    merchant=txn.merchant,
                    amount=txn.amount,
                    category=categorization_item.category,
                    anomaly_type=anomaly_type,
                    anomaly_reason=anomaly_reason,
                    confidence=categorization_item.confidence,
                )
            )

        connection.commit()

    anomalies_count = sum(1 for item in response_items if item.anomaly_type)
    return UploadResponse(
        upload_id=upload_id,
        transactions=response_items,
        anomalies_count=anomalies_count,
    )
