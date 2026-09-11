import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from unibiz.core.config import get_settings
from unibiz.core.database import get_db
from unibiz.core.security import hash_password
from unibiz.models.system import DataScope, Role, User
from unibiz.schemas.auth import BootstrapAdminRequest, BootstrapStatus

router = APIRouter(prefix="/system/bootstrap", tags=["bootstrap"])


@router.get("/status", response_model=BootstrapStatus)
async def bootstrap_status(db: AsyncSession = Depends(get_db)) -> BootstrapStatus:
    count = await db.scalar(select(func.count()).select_from(User))
    return BootstrapStatus(initialized=bool(count))


@router.post("/admin", status_code=status.HTTP_201_CREATED)
async def create_first_admin(
    payload: BootstrapAdminRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    settings = get_settings()
    if not secrets.compare_digest(payload.bootstrap_token, settings.bootstrap_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid bootstrap token")

    # Transaction-scoped advisory lock prevents two concurrent first-admin requests.
    await db.execute(text("SELECT pg_advisory_xact_lock(843216731)"))
    count = await db.scalar(select(func.count()).select_from(User))
    if count:
        raise HTTPException(status.HTTP_409_CONFLICT, "System is already initialized")

    role = Role(
        name="超级管理员",
        code="super_admin",
        is_system=True,
        view_scope=DataScope.ALL,
        edit_scope=DataScope.ALL,
    )
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        enabled=True,
        is_superuser=True,
        roles=[role],
    )
    db.add(user)
    await db.commit()
    return {"id": str(user.id)}
