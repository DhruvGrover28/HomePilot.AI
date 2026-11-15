from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    theme_preference: str = "system"


class AuthResponse(BaseModel):
    user: UserOut
    household_id: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    theme_preference: str | None = Field(default=None, pattern="^(light|dark|system)$")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class HouseholdOut(BaseModel):
    id: str
    name: str
    timezone: str = "UTC"
    preferred_units: str = "metric"
    onboarding_completed: bool = False


class UpdateHouseholdRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    timezone: str | None = Field(default=None, max_length=50)
    preferred_units: str | None = Field(default=None, pattern="^(metric|imperial)$")
    onboarding_completed: bool | None = None

