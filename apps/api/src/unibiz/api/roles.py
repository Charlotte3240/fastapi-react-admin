from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.system import Permission, Role, User
from unibiz.schemas.system import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/system", tags=["roles"])
RoleViewer = Annotated[User, Depends(require_permission("system:role:view"))]
RoleManager = Annotated[User, Depends(require_permission("system:role:manage"))]


async def permissions_from_codes(db: AsyncSession, codes: list[str]) -> list[Permission]:
    unique_codes = set(codes)
    permissions = list(
        (await db.scalars(select(Permission).where(Permission.code.in_(unique_codes)))).all()
    )
    found = {permission.code for permission in permissions}
    if missing := unique_codes - found:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unknown permission codes: {', '.join(sorted(missing))}",
        )
    return permissions


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(_: RoleViewer, db: DbSession) -> list[Permission]:
    return list(
        (await db.scalars(select(Permission).order_by(Permission.module, Permission.code))).all()
    )


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(_: RoleViewer, db: DbSession) -> list[Role]:
    query = (
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.is_system.desc(), Role.name)
    )
    return list((await db.scalars(query)).all())


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreate, _: RoleManager, db: DbSession) -> Role:
    if await db.scalar(select(Role.id).where(Role.code == payload.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Role code already exists")
    role = Role(
        name=payload.name,
        code=payload.code,
        view_scope=payload.view_scope,
        edit_scope=payload.edit_scope,
        permissions=await permissions_from_codes(db, payload.permission_codes),
    )
    db.add(role)
    await db.commit()
    await db.refresh(role, attribute_names=["permissions"])
    return role


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: UUID, payload: RoleUpdate, _: RoleManager, db: DbSession) -> Role:
    role = await db.scalar(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    if role.is_system:
        raise HTTPException(status.HTTP_409_CONFLICT, "System roles cannot be modified")
    changes = payload.model_dump(exclude_unset=True, exclude={"permission_codes"})
    for field, value in changes.items():
        setattr(role, field, value)
    if payload.permission_codes is not None:
        role.permissions = await permissions_from_codes(db, payload.permission_codes)
    await db.commit()
    return role
