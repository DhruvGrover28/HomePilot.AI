from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Household
from app.db.session import SessionLocal
from app.services.monitoring import monitor_and_investigate
from app.services.monitoring_executor import (
    MonitoringExecutor,
    recover_stale_investigations,
)


class MonitoringRuntime:
    def __init__(self) -> None:
        self._executor: MonitoringExecutor | None = None
        self._scheduler: BackgroundScheduler | None = None

    def start(self) -> None:
        settings = get_settings()
        if self._executor is not None:
            return
        recover_stale_investigations(settings.monitoring_claim_timeout_minutes)
        self._executor = MonitoringExecutor(
            max_workers=settings.monitoring_max_workers,
            max_pending_jobs=settings.monitoring_max_pending_jobs,
        )
        self._executor.start()
        if settings.monitoring_enabled:
            self._scheduler = BackgroundScheduler()
            self._scheduler.add_job(
                self.run_scheduled_check,
                "interval",
                minutes=settings.monitoring_interval_minutes,
                id="household-monitoring",
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
            self._scheduler.start()

    def stop(self) -> None:
        scheduler, executor = self._scheduler, self._executor
        self._scheduler = None
        self._executor = None
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        if executor is not None:
            executor.shutdown()

    def run_scheduled_check(self) -> None:
        if self._executor is None:
            return
        settings = get_settings()
        recover_stale_investigations(
            settings.monitoring_claim_timeout_minutes,
            self._executor.in_flight_investigation_ids(),
        )
        with SessionLocal() as session:
            household_ids = session.scalars(select(Household.id)).all()
        for household_id in household_ids:
            monitor_and_investigate(
                "scheduled",
                domains=None,
                executor=self._executor,
                household_id=household_id,
            )

    def trigger_event(self, domains: list[str], household_id: str | None = None) -> None:
        if self._executor is None:
            return
        monitor_and_investigate(
            "event",
            domains=domains,
            executor=self._executor,
            household_id=household_id,
        )

    def trigger_manual(
        self,
        domains: list[str] | None = None,
        household_id: str | None = None,
    ) -> list:
        if self._executor is None:
            raise RuntimeError("Monitoring runtime is not started.")
        return monitor_and_investigate(
            "manual",
            domains=domains,
            executor=self._executor,
            household_id=household_id,
        )


monitoring_runtime = MonitoringRuntime()
