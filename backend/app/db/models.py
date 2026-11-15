from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    theme_preference: Mapped[str] = mapped_column(String(20), default="system", nullable=False)


class Household(Timestamped, Base):
    __tablename__ = "households"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    preferred_units: Mapped[str] = mapped_column(String(20), default="metric", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AssistantMessage(Timestamped, Base):
    __tablename__ = "assistant_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class UserSession(Timestamped, Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Reading(Timestamped, Base):
    __tablename__ = "readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    meter_value: Mapped[float | None] = mapped_column(Float)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    consumption: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Appliance(Timestamped, Base):
    __tablename__ = "appliances"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    rated_watts: Mapped[float | None] = mapped_column(Float)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    warranty_end: Mapped[date | None] = mapped_column(Date)
    last_service_date: Mapped[date | None] = mapped_column(Date)
    service_interval_days: Mapped[int | None] = mapped_column(Integer)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class InventoryItem(Timestamped, Base):
    __tablename__ = "inventory_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    reorder_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class InventoryLog(Timestamped, Base):
    __tablename__ = "inventory_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ShoppingListItem(Timestamped, Base):
    __tablename__ = "shopping_list"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)


class Task(Timestamped, Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    appliance_id: Mapped[int | None] = mapped_column(ForeignKey("appliances.id"))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)


class AgentRun(Timestamped, Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    domains: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    trace_json: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=False)


class MonitoringIssue(Timestamped, Base):
    __tablename__ = "monitoring_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(60), nullable=False)
    domain: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    issue_status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    first_trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    last_trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    latest_evidence_id: Mapped[int | None] = mapped_column(Integer)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    investigation_id: Mapped[str | None] = mapped_column(String(36))
    investigation_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    active_run_id: Mapped[str | None] = mapped_column(String(36))
    latest_run_id: Mapped[str | None] = mapped_column(String(36))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class UtilityBill(Timestamped, Base):
    __tablename__ = "utility_bills"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), index=True)
    utility_type: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(160))
    account_number: Mapped[str | None] = mapped_column(String(80))
    bill_number: Mapped[str | None] = mapped_column(String(80))
    bill_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    previous_reading: Mapped[float | None] = mapped_column(Float)
    current_reading: Mapped[float | None] = mapped_column(Float)
    consumption: Mapped[float] = mapped_column(Float, nullable=False)
    consumption_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    total_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    fixed_charges: Mapped[float | None] = mapped_column(Float)
    variable_charges: Mapped[float | None] = mapped_column(Float)
    taxes: Mapped[float | None] = mapped_column(Float)
    other_charges: Mapped[float | None] = mapped_column(Float)
    csv_content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_data_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
