from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.agent_service import get_agent_run
from app.services.auth import get_current_household
from app.services.monitoring import get_monitoring_issue, list_monitoring_issues
from app.services.monitoring_runtime import monitoring_runtime

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class ManualMonitoringRequest(BaseModel):
    domains: list[Literal["energy", "water", "maintenance", "inventory"]] = Field(
        default_factory=list
    )


@router.get("/issues")
def read_monitoring_issues(
    issue_status: Literal["open", "resolved"] | None = Query(default=None),
    household=Depends(get_current_household),
) -> list[dict]:
    response = []
    for issue in list_monitoring_issues(
        issue_status=issue_status,
        household_id=household.id,
    ):
        item = issue.model_dump()
        if issue.latest_run_id:
            item["latest_run"] = get_agent_run(
                issue.latest_run_id,
                household_id=household.id,
            )
        response.append(item)
    return response


@router.get("/issues/{issue_id}")
def read_monitoring_issue(issue_id: str, household=Depends(get_current_household)) -> dict:
    issue = get_monitoring_issue(
        issue_id,
        household_id=household.id,
    )
    if issue is None:
        raise HTTPException(404, "Monitoring issue not found.")
    response = issue.model_dump()
    if issue.latest_run_id:
        response["latest_run"] = get_agent_run(
            issue.latest_run_id,
            household_id=household.id,
        )
    return response


@router.post("/check")
def run_manual_monitoring(
    payload: ManualMonitoringRequest,
    household=Depends(get_current_household),
) -> list[dict]:
    try:
        issues = monitoring_runtime.trigger_manual(
            payload.domains or None,
            household.id,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return [issue.model_dump() for issue in issues]
