from fastapi import APIRouter, Depends

from app.schemas_agents import UpdateRecommendationStatusRequest
from app.services.auth import get_current_household
from app.services.household_intelligence import (
    build_household_intelligence,
    update_recommendation_status,
)

router = APIRouter(prefix="/api", tags=["intelligence"])


@router.get("/intelligence/summary")
def read_intelligence_summary(household=Depends(get_current_household)) -> dict:
    return build_household_intelligence(household.id)


@router.patch("/recommendations/{recommendation_id}")
def patch_recommendation_status(
    recommendation_id: str,
    payload: UpdateRecommendationStatusRequest,
    household=Depends(get_current_household),
) -> dict:
    return update_recommendation_status(recommendation_id, payload.status, household.id)
