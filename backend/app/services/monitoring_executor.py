from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
import logging
from threading import BoundedSemaphore, Lock
from typing import Any

from sqlalchemy import select

from app import clock
from app.db.models import MonitoringIssue
from app.db.session import SessionLocal
from app.schemas_agents import AgentRunCreate, InvestigationContext
from app.services.agent_service import run_agent


logger = logging.getLogger(__name__)


class MonitoringExecutor:
    def __init__(self, *, max_workers: int = 2, max_pending_jobs: int = 4) -> None:
        if max_workers < 1 or max_pending_jobs < 0:
            raise ValueError("Monitoring executor capacity must be positive.")
        self._max_workers = max_workers
        self._max_slots = max_workers + max_pending_jobs
        self._executor: ThreadPoolExecutor | None = None
        self._slots: BoundedSemaphore | None = None
        self._lock = Lock()
        self._futures: dict[str, Future[Any]] = {}
        self._accepting = False

    def start(self) -> None:
        with self._lock:
            if self._accepting:
                return
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="homepilot-monitoring",
            )
            self._slots = BoundedSemaphore(self._max_slots)
            self._accepting = True

    def submit(
        self,
        issue_id: str,
        investigation_id: str,
        goal: str,
        domains: list[str],
        *,
        investigation_context: InvestigationContext | None = None,
        household_id: str | None = None,
    ) -> bool:
        with self._lock:
            executor = self._executor
            slots = self._slots
            if not self._accepting or executor is None or slots is None or not slots.acquire(blocking=False):
                logger.warning("Monitoring executor rejected issue %s: capacity unavailable.", issue_id)
                self._mark_interrupted(issue_id, "Monitoring executor capacity is unavailable.")
                return False
            try:
                future = executor.submit(
                    self._run_investigation,
                    issue_id,
                    investigation_id,
                    goal,
                    domains,
                    investigation_context,
                    household_id,
                )
            except RuntimeError as exc:
                slots.release()
                self._mark_interrupted(issue_id, "Monitoring executor rejected the investigation.")
                logger.warning(
                    "Monitoring executor rejected issue %s during submission: %s",
                    issue_id,
                    exc,
                )
                return False
            self._futures[investigation_id] = future
            future.add_done_callback(
                lambda completed, acquired_slots=slots: self._complete_future(
                    investigation_id,
                    completed,
                    acquired_slots,
                )
            )
            return True

    def shutdown(self) -> None:
        with self._lock:
            self._accepting = False
            executor = self._executor
            futures = list(self._futures.items())
            self._executor = None
            self._slots = None
        if executor is None:
            return
        for investigation_id, future in futures:
            if future.cancel():
                issue_id = self._issue_id_for(investigation_id)
                if issue_id:
                    self._mark_interrupted(issue_id, "Monitoring investigation interrupted during shutdown.")
        executor.shutdown(wait=False, cancel_futures=True)

    def in_flight_investigation_ids(self) -> set[str]:
        with self._lock:
            return set(self._futures)

    def _run_investigation(
        self,
        issue_id: str,
        investigation_id: str,
        goal: str,
        domains: list[str],
        investigation_context: InvestigationContext | None = None,
        household_id: str | None = None,
    ) -> None:
        try:
            started_at = clock.now()
            with SessionLocal() as session:
                issue = session.get(MonitoringIssue, issue_id)
                if (
                    issue is None
                    or issue.investigation_id != investigation_id
                    or (
                        household_id is not None
                        and issue.household_id != household_id
                    )
                ):
                    return
                issue.investigation_status = "investigating"
                issue.started_at = started_at
                session.commit()
            payload = AgentRunCreate(
                goal=goal,
                domains=domains,
                investigation_context=investigation_context,
            )
            if household_id is None:
                result = run_agent(payload)
            else:
                result = run_agent(payload, household_id=household_id)
            investigation_status = (
                "provider_exhausted"
                if result.get("stop_reason") == "provider_exhausted"
                else "completed"
            )
            with SessionLocal() as session:
                issue = session.get(MonitoringIssue, issue_id)
                if (
                    issue is None
                    or issue.investigation_id != investigation_id
                    or (
                        household_id is not None
                        and issue.household_id != household_id
                    )
                ):
                    return
                issue.investigation_status = investigation_status
                issue.active_run_id = None
                issue.latest_run_id = result["id"]
                issue.completed_at = clock.now()
                issue.last_error = None
                session.commit()
        except Exception as exc:
            logger.exception("Monitoring investigation %s failed.", investigation_id)
            self._mark_failed(issue_id, investigation_id, str(exc)[:500])

    def _complete_future(
        self,
        investigation_id: str,
        future: Future[Any],
        acquired_slots: BoundedSemaphore,
    ) -> None:
        with self._lock:
            self._futures.pop(investigation_id, None)
        acquired_slots.release()

    def _issue_id_for(self, investigation_id: str) -> str | None:
        with SessionLocal() as session:
            issue = session.scalar(
                select(MonitoringIssue).where(
                    MonitoringIssue.investigation_id == investigation_id
                )
            )
            return issue.id if issue else None

    @staticmethod
    def _mark_interrupted(issue_id: str, message: str) -> None:
        with SessionLocal() as session:
            issue = session.get(MonitoringIssue, issue_id)
            if issue is None:
                return
            issue.investigation_status = "interrupted"
            issue.active_run_id = None
            issue.completed_at = clock.now()
            issue.last_error = message
            session.commit()

    @staticmethod
    def _mark_failed(issue_id: str, investigation_id: str, message: str) -> None:
        try:
            with SessionLocal() as session:
                issue = session.get(MonitoringIssue, issue_id)
                if issue is None or issue.investigation_id != investigation_id:
                    return
                issue.investigation_status = "failed"
                issue.active_run_id = None
                issue.completed_at = clock.now()
                issue.last_error = message
                session.commit()
        except Exception:
            logger.exception(
                "Unable to persist failed monitoring investigation %s.",
                investigation_id,
            )


def recover_stale_investigations(
    claim_timeout_minutes: int,
    protected_investigation_ids: set[str] | None = None,
) -> int:
    cutoff = clock.now() - timedelta(minutes=claim_timeout_minutes)
    protected = protected_investigation_ids or set()
    recovered = 0
    with SessionLocal() as session:
        issues = session.scalars(
            select(MonitoringIssue).where(
                MonitoringIssue.investigation_status.in_(("queued", "investigating")),
                MonitoringIssue.claimed_at < cutoff,
            )
        ).all()
        for issue in issues:
            if issue.investigation_id in protected:
                continue
            issue.investigation_status = "interrupted"
            issue.active_run_id = None
            issue.completed_at = clock.now()
            issue.last_error = "Recovered stale monitoring investigation."
            recovered += 1
        session.commit()
    return recovered
