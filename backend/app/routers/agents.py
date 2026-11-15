from fastapi import APIRouter, Depends, HTTPException
from google.api_core.exceptions import GoogleAPIError

from app.schemas_agents import AgentRunCreate
from app.services.auth import get_current_household
from app.services.agent_service import get_agent_run, run_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/runs")
def create_agent_run(
    payload: AgentRunCreate,
    household=Depends(get_current_household),
) -> dict:
    try:
        return run_agent(payload, household_id=household.id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except GoogleAPIError as exc:
        raise HTTPException(502, "Agent provider failed to complete the run.") from exc


@router.get("/runs/{run_id}")
def read_agent_run(run_id: str, household=Depends(get_current_household)) -> dict:
    run = get_agent_run(run_id, household_id=household.id)
    if run is None:
        raise HTTPException(404, "Agent run not found.")
    return run
