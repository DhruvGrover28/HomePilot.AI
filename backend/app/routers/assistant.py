from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.services.assistant_service import (
    clear_assistant_history,
    get_assistant_history,
    handle_assistant_message,
)
from app.services.auth import get_current_household

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class AssistantChatResponse(BaseModel):
    reply: str
    suggested_prompts: list[str] = Field(default_factory=list)
    related_issues: list[dict[str, Any]] = Field(default_factory=list)
    related_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    agent_run: dict[str, Any] | None = None


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    payload: AssistantChatRequest,
    household=Depends(get_current_household),
) -> dict:
    return handle_assistant_message(payload.message, household.id)


@router.get("/history")
def history(
    household=Depends(get_current_household),
) -> list[dict]:
    return get_assistant_history(household.id)


@router.delete("/history", status_code=204, response_class=Response)
def clear_history(
    household=Depends(get_current_household),
) -> Response:
    clear_assistant_history(household.id)
    return Response(status_code=204)
