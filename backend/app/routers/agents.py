from fastapi import APIRouter, HTTPException
from google.api_core.exceptions import GoogleAPIError

from app.schemas_agents import AgentRunCreate
from app.services.agent_service import get_agent_run, run_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/runs")
def create_agent_run(payload: AgentRunCreate) -> dict:
    try:
        return run_agent(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except GoogleAPIError as exc:
        raise HTTPException(502, "Agent provider failed to complete the run.") from exc


@router.get("/runs/{run_id}")
def read_agent_run(run_id: str) -> dict:
    run = get_agent_run(run_id)
    if run is None:
        raise HTTPException(404, "Agent run not found.")
    return run
