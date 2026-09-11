from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unibiz.api.dependencies import CurrentUser, permission_codes
from unibiz.core.config import get_settings
from unibiz.core.database import get_db
from unibiz.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from unibiz.models.system import RefreshSession, User
from unibiz.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
DUMMY_PASSWORD_HASH = hash_password("not-a-real-account-password")


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        "refresh_token",
        raw_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    user = await db.scalar(select(User).where(User.username == payload.username).with_for_update())
    now = datetime.now(UTC)
    if user and user.locked_until and user.locked_until <= now:
        user.locked_until = None
        user.failed_login_count = 0
    password_valid = verify_password(
        payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )
    valid = bool(
        user and user.enabled and not user.deleted_at and not user.locked_until and password_valid
    )
    if not valid:
        if user and user.enabled and not user.deleted_at and not user.locked_until:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    assert user is not None
    user.failed_login_count = 0
    user.locked_until = None
    raw_refresh, refresh_hash = new_opaque_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.commit()
    request.state.audit_actor_id = user.id
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is missing")
    session = await db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_refresh))
    )
    now = datetime.now(UTC)
    if not session or session.revoked_at or session.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is invalid")
    user = await db.get(User, session.user_id)
    if not user or not user.enabled or user.deleted_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is unavailable")

    session.revoked_at = now
    new_raw, new_hash = new_opaque_token()
    settings = get_settings()
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.commit()
    request.state.audit_actor_id = user.id
    set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        session = await db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_refresh))
        )
        if session and not session.revoked_at:
            session.revoked_at = datetime.now(UTC)
            await db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        permissions=sorted(permission_codes(user)),
        is_superuser=user.is_superuser,
    )
