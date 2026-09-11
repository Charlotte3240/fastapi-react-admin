from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from unibiz.core.database import get_db
from unibiz.core.security import decode_access_token, hash_token
from unibiz.models.integration import ServiceAccount, ServiceApiKey
from unibiz.models.system import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]
BearerToken = Annotated[str | None, Depends(oauth2_scheme)]
ApiKeyToken = Annotated[str | None, Depends(api_key_scheme)]


async def get_current_user(
    request: Request, token: BearerToken, api_key: ApiKeyToken, db: DbSession
) -> User:
    if api_key:
        now = datetime.now(UTC)
        row = (
            await db.execute(
                select(ServiceApiKey, ServiceAccount, User)
                .join(ServiceAccount, ServiceAccount.id == ServiceApiKey.service_account_id)
                .join(User, User.id == ServiceAccount.user_id)
                .where(
                    ServiceApiKey.secret_hash == hash_token(api_key),
                    ServiceApiKey.revoked_at.is_(None),
                    (ServiceApiKey.expires_at.is_(None) | (ServiceApiKey.expires_at > now)),
                    ServiceAccount.enabled.is_(True),
                    (ServiceAccount.expires_at.is_(None) | (ServiceAccount.expires_at > now)),
                )
                .options(selectinload(ServiceAccount.permissions))
            )
        ).first()
        if not row:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
        _, account, user = row
        account.last_used_at = now
        await db.commit()
        user._service_permission_codes = {item.code for item in account.permissions}
        user._service_data_scope = "all"
        request.state.audit_actor_id = user.id
        return user
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        user_id = decode_access_token(token)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid access token") from None
    user = await db.scalar(
        select(User)
        .where(User.id == user_id, User.enabled.is_(True), User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is unavailable")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def permission_codes(user: User) -> set[str]:
    service_permissions = getattr(user, "_service_permission_codes", None)
    if service_permissions is not None:
        return set(service_permissions)
    if user.is_superuser:
        return set()
    return {
        permission.code for role in user.roles if role.enabled for permission in role.permissions
    }


def require_permission(code: str) -> Callable[[CurrentUser], Awaitable[User]]:
    async def dependency(user: CurrentUser) -> User:
        if not user.is_superuser and code not in permission_codes(user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {code}")
        return user

    return dependency


def effective_scope(user: User, attribute: str) -> str:
    service_scope = getattr(user, "_service_data_scope", None)
    if service_scope is not None:
        return str(service_scope)
    if user.is_superuser:
        return "all"
    rank = {"self": 0, "department": 1, "all": 2}
    scopes = [getattr(role, attribute) for role in user.roles if role.enabled]
    return max(scopes, key=lambda item: rank[item], default="self")
