from fastapi import APIRouter, Depends, Request, Response

from app.schemas_auth import (
    AuthResponse,
    ChangePasswordRequest,
    HouseholdOut,
    LoginRequest,
    RegisterRequest,
    UpdateHouseholdRequest,
    UpdateProfileRequest,
    UserOut,
)
from app.services.auth import (
    change_user_password,
    get_current_household,
    get_current_user,
    login_user,
    register_user,
    revoke_session,
    update_household_settings,
    update_user_profile,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, response: Response) -> AuthResponse:
    return register_user(payload, response)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    return login_user(payload, response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    revoke_session(request, response)


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        theme_preference=getattr(user, "theme_preference", "system") or "system",
    )


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: UpdateProfileRequest,
    user=Depends(get_current_user),
) -> UserOut:
    return update_user_profile(user.id, payload)


@router.delete("/me", status_code=204)
def delete_account(
    request: Request,
    response: Response,
    user=Depends(get_current_user),
) -> None:
    from app.services.auth import delete_user_account
    delete_user_account(user.id, request, response)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user=Depends(get_current_user),
) -> dict[str, str]:
    change_user_password(user.id, payload)
    return {"status": "ok", "message": "Password updated successfully."}


@router.get("/household", response_model=HouseholdOut)
def household(household=Depends(get_current_household)) -> HouseholdOut:
    return HouseholdOut(
        id=household.id,
        name=household.name,
        timezone=getattr(household, "timezone", "UTC") or "UTC",
        preferred_units=getattr(household, "preferred_units", "metric") or "metric",
        onboarding_completed=bool(getattr(household, "onboarding_completed", False)),
    )


@router.patch("/household", response_model=HouseholdOut)
def update_household(
    payload: UpdateHouseholdRequest,
    household=Depends(get_current_household),
) -> HouseholdOut:
    return update_household_settings(household.id, payload)
