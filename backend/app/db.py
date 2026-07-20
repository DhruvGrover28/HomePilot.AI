from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "homepilot.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id TEXT NOT NULL,
                txn_date TEXT NOT NULL,
                description TEXT NOT NULL,
                merchant TEXT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                anomaly_type TEXT,
                anomaly_reason TEXT,
                confidence REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
