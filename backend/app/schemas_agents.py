from typing import Literal

from pydantic import BaseModel, Field

AgentDomain = Literal["energy", "maintenance", "inventory"]


class AgentRunCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=500)
    domains: list[AgentDomain] = Field(default_factory=list, max_length=3)


class AgentRunOut(BaseModel):
    id: str
    goal: str
    domains: list[str]
    status: str
    mode: str
    trace: list[dict]
    recommendations: list[dict]
    created_at: str
