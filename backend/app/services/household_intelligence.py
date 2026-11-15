from __future__ import annotations

from collections import Counter
from typing import Any

from app.schemas_monitoring import MonitoringIssueOut
from app.services.agent_service import get_agent_run
from app.services.intelligence import (
    monitoring_priority_factors,
    monitoring_priority_key,
    recommendation_priority_factors,
    recommendation_priority_key,
)
from app.services.monitoring import classify_issue_relationship, list_monitoring_issues


def _issue_priority(issue: MonitoringIssueOut, issues: list[MonitoringIssueOut]) -> dict[str, Any]:
    corroboration = sum(
        classify_issue_relationship(issue, other).relationship == "confirmed"
        for other in issues
        if other.id != issue.id
    )
    factors = monitoring_priority_factors(issue)
    factors["corroboration"] = min(2, corroboration)
    return {
        "factors": factors,
        "key": monitoring_priority_key(issue, corroboration_level=corroboration),
    }


def build_household_intelligence(household_id: str | None = None) -> dict[str, Any]:
    try:
        open_issues = list_monitoring_issues(
            issue_status="open",
            household_id=household_id,
        )
    except TypeError:
        open_issues = list_monitoring_issues(issue_status="open")
    ranked = sorted(
        open_issues,
        key=lambda issue: _issue_priority(issue, open_issues)["key"],
        reverse=True,
    )
    issue_by_id = {issue.id: issue for issue in open_issues}
    issue_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    run_statuses: Counter[str] = Counter()

    for issue in ranked:
        priority = _issue_priority(issue, open_issues)
        if issue.latest_run_id:
            run = (
                get_agent_run(issue.latest_run_id)
                if household_id is None
                else get_agent_run(issue.latest_run_id, household_id=household_id)
            )
        else:
            run = None
        if run:
            run_statuses[run["status"]] += 1
            for index, finding in enumerate(run.get("findings", [])):
                findings.append(
                    {
                        "id": finding["id"],
                        "issue_id": issue.id,
                        "run_id": run["id"],
                        "finding": finding,
                    }
                )
            for index, recommendation in enumerate(run.get("recommendations", [])):
                recommendation_id = f"{run['id']}:{index}"
                factors = recommendation_priority_factors(
                    recommendation,
                    run.get("findings", []),
                    issue,
                )
                recommendations.append(
                    {
                        "id": recommendation_id,
                        "issue_id": issue.id,
                        "run_id": run["id"],
                        "recommendation": recommendation,
                        "_findings": run.get("findings", []),
                        "priority_factors": factors,
                        "_key": recommendation_priority_key(
                            recommendation,
                            run.get("findings", []),
                            issue,
                            recommendation_id=recommendation_id,
                        ),
                    }
                )
        issue_rows.append(
            {
                **issue.model_dump(mode="json"),
                "priority_factors": priority["factors"],
                "investigation": {
                    "status": issue.investigation_status,
                    "run_id": issue.latest_run_id,
                },
            }
        )

    relationships = []
    for index, primary in enumerate(ranked):
        for related in ranked[index + 1 :]:
            relationship = classify_issue_relationship(primary, related)
            if relationship.relationship != "unrelated":
                relationships.append(
                    {
                        "primary_issue_id": primary.id,
                        "related_issue_id": related.id,
                        **relationship.model_dump(),
                    }
                )

    for recommendation in recommendations:
        recommendation.pop("_key", None)
    recommendations.sort(
        key=lambda item: recommendation_priority_key(
            item["recommendation"],
            item["_findings"],
            issue_by_id.get(item["issue_id"]),
            recommendation_id=item["id"],
        ),
        reverse=True,
    )
    for recommendation in recommendations:
        recommendation.pop("_findings", None)
    return {
        "open_issues": issue_rows,
        "relationships": relationships,
        "findings": findings,
        "recommendations": recommendations,
        "investigation_statuses": dict(run_statuses),
        "warnings": [
            {
                "issue_id": issue.id,
                "title": issue.title,
                "reason": "Evidence is incomplete or insufficient for confirmed prioritisation.",
            }
            for issue in ranked
            if monitoring_priority_factors(issue)["evidence_state"] == 0
        ],
    }


def update_recommendation_status(
    recommendation_id: str,
    status: str,
    household_id: str,
) -> dict[str, Any]:
    import json
    from fastapi import HTTPException
    from app.db.models import AgentRun
    from app.db.session import SessionLocal

    parts = recommendation_id.split(":")
    if len(parts) != 2:
        raise HTTPException(400, "Invalid recommendation ID format. Expected run_id:index.")
    run_id, index_str = parts
    try:
        index = int(index_str)
    except ValueError:
        raise HTTPException(400, "Invalid recommendation index.")

    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        if run is None or run.household_id != household_id:
            raise HTTPException(404, "Recommendation not found.")

        try:
            recs = json.loads(run.recommendations_json)
        except Exception:
            raise HTTPException(500, "Corrupt recommendation payload.")

        if index < 0 or index >= len(recs):
            raise HTTPException(404, "Recommendation index out of range.")

        recs[index]["status"] = status
        run.recommendations_json = json.dumps(recs)
        session.commit()
        return recs[index]
