from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.session import engine


_OWNERSHIP_TABLES = (
    "readings",
    "appliances",
    "inventory_items",
    "inventory_log",
    "shopping_list",
    "tasks",
    "agent_runs",
    "monitoring_issues",
)

_CUSTOM_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("theme_preference", "VARCHAR(20) DEFAULT 'system'"),
    ],
    "households": [
        ("timezone", "VARCHAR(50) DEFAULT 'UTC'"),
        ("preferred_units", "VARCHAR(20) DEFAULT 'metric'"),
        ("onboarding_completed", "BOOLEAN DEFAULT 0"),
    ],
}


def apply_additive_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table in _OWNERSHIP_TABLES:
            if table not in existing_tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "household_id" not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table} "
                        "ADD COLUMN household_id VARCHAR(36)"
                    )
                )
        for table, col_defs in _CUSTOM_COLUMNS.items():
            if table not in existing_tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            for col_name, col_type in col_defs:
                if col_name not in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table} "
                            f"ADD COLUMN {col_name} {col_type}"
                        )
                    )
