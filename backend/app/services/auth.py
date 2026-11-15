from __future__ import annotations

from datetime import timedelta
import hashlib
import hmac
import re
import secrets
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import Household, User, UserSession
from app.db.session import SessionLocal
from app.schemas_auth import AuthResponse, UserOut


SESSION_COOKIE = "homepilot_session"
SESSION_TTL = timedelta(hours=12)
_PBKDF2_ITERATIONS = 600_000


def _hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _email(value: str) -> str:
    normalized = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise HTTPException(422, "A valid email address is required.")
    return normalized


from app.schemas_auth import AuthResponse, HouseholdOut, UserOut


def _user_response(user: User, household: Household) -> AuthResponse:
    return AuthResponse(
        user=UserOut(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            theme_preference=getattr(user, "theme_preference", "system") or "system",
        ),
        household_id=household.id,
    )


def update_user_profile(user_id: str, payload) -> UserOut:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(404, "User not found.")
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.theme_preference is not None:
            user.theme_preference = payload.theme_preference
        session.commit()
        session.refresh(user)
        return UserOut(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            theme_preference=user.theme_preference,
        )


def change_user_password(user_id: str, payload) -> None:
    if payload.new_password != payload.confirm_password:
        raise HTTPException(422, "Passwords do not match.")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(404, "User not found.")
        if not _verify_password(payload.current_password, user.password_hash):
            raise HTTPException(400, "Current password is incorrect.")
        user.password_hash = _hash_password(payload.new_password)
        session.commit()


def update_household_settings(household_id: str, payload) -> HouseholdOut:
    with SessionLocal() as session:
        household = session.get(Household, household_id)
        if household is None:
            raise HTTPException(404, "Household not found.")
        if payload.name is not None:
            household.name = payload.name.strip()
        if payload.timezone is not None:
            household.timezone = payload.timezone.strip()
        if payload.preferred_units is not None:
            household.preferred_units = payload.preferred_units
        if payload.onboarding_completed is not None:
            household.onboarding_completed = payload.onboarding_completed
        session.commit()
        session.refresh(household)
        return HouseholdOut(
            id=household.id,
            name=household.name,
            timezone=household.timezone,
            preferred_units=household.preferred_units,
            onboarding_completed=household.onboarding_completed,
        )


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        secure=get_settings().session_cookie_secure,
        samesite="lax",
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
    )


def register_user(payload, response: Response) -> AuthResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(422, "Passwords do not match.")
    email = _email(str(payload.email))
    now = clock.now()
    with SessionLocal() as session:
        if session.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, "An account with that email already exists.")
        user = User(
            id=str(uuid4()),
            full_name=payload.full_name.strip(),
            email=email,
            password_hash=_hash_password(payload.password),
            created_at=now,
        )
        household = Household(
            id=str(uuid4()),
            name=f"{user.full_name}'s household",
            owner_id=user.id,
            created_at=now,
        )
        session.add_all([user, household])
        session.flush()
        _create_session(session, user.id, response)
        session.commit()
        return _user_response(user, household)


def login_user(payload, response: Response) -> AuthResponse:
    email = _email(str(payload.email))
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None or not _verify_password(payload.password, user.password_hash):
            raise HTTPException(401, "Invalid email or password.")
        household = session.scalar(select(Household).where(Household.owner_id == user.id))
        if household is None:
            raise HTTPException(409, "Account household is not configured.")
        _create_session(session, user.id, response)
        session.commit()
        return _user_response(user, household)


def _create_session(session, user_id: str, response: Response) -> None:
    raw_token = secrets.token_urlsafe(32)
    session.add(
        UserSession(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=clock.now() + SESSION_TTL,
            created_at=clock.now(),
        )
    )
    _set_session_cookie(response, raw_token)


def revoke_session(request: Request, response: Response) -> None:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if raw_token:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        with SessionLocal() as session:
            row = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
            if row is not None:
                row.revoked_at = clock.now()
                session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def delete_user_account(user_id: str, request: Request, response: Response) -> None:
    from sqlalchemy import delete
    revoke_session(request, response)
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            session.execute(delete(UserSession).where(UserSession.user_id == user_id))
            session.delete(user)
            session.commit()


def get_current_user(request: Request) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()
        else:
            raw_token = request.headers.get("X-Session-Token")
    if not raw_token:
        raise HTTPException(401, "Authentication is required.")
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with SessionLocal() as session:
        row = session.scalar(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > clock.now(),
            )
        )
        if row is None:
            raise HTTPException(401, "Authentication is required.")
        user = session.get(User, row.user_id)
        if user is None:
            raise HTTPException(401, "Authentication is required.")
        session.expunge(user)
        return user


def get_current_household(user: User = Depends(get_current_user)) -> Household:
    with SessionLocal() as session:
        household = session.scalar(select(Household).where(Household.owner_id == user.id))
        if household is None:
            raise HTTPException(409, "Account household is not configured.")
        session.expunge(household)
        return household


def get_optional_household(request: Request) -> Household | None:
    raw_token = request.cookies.get(SESSION_COOKIE) or request.headers.get("X-Session-Token")
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()
    if not raw_token:
        return None
    try:
        user = get_current_user(request)
    except HTTPException:
        return None
    with SessionLocal() as session:
        household = session.scalar(select(Household).where(Household.owner_id == user.id))
        if household is None:
            return None
        session.expunge(household)
        return household
