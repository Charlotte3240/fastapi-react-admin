from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.core.security import hash_password
from unibiz.models.system import Department, Position, Role, User
from unibiz.schemas.organization import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/system/users", tags=["users"])
UserViewer = Annotated[User, Depends(require_permission("system:user:view"))]
UserManager = Annotated[User, Depends(require_permission("system:user:manage"))]


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        department_id=user.department_id,
        enabled=user.enabled,
        is_superuser=user.is_superuser,
        roles=[{"id": str(role.id), "name": role.name, "code": role.code} for role in user.roles],
        positions=[
            {"id": str(position.id), "name": position.name, "code": position.code}
            for position in user.positions
        ],
    )


async def assignable_roles(db: DbSession, ids: list[UUID]) -> list[Role]:
    roles = list((await db.scalars(select(Role).where(Role.id.in_(set(ids))))).all())
    if len(roles) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "One or more roles not found")
    if any(role.is_system for role in roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "System roles cannot be assigned")
    return roles


async def assignable_positions(db: DbSession, ids: list[UUID]) -> list[Position]:
    positions = list((await db.scalars(select(Position).where(Position.id.in_(set(ids))))).all())
    if len(positions) != len(set(ids)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "One or more positions not found"
        )
    return positions


@router.get("", response_model=list[UserResponse])
async def list_users(_: UserViewer, db: DbSession) -> list[UserResponse]:
    users = list(
        (
            await db.scalars(
                select(User)
                .where(User.deleted_at.is_(None))
                .options(selectinload(User.roles), selectinload(User.positions))
                .order_by(User.created_at)
            )
        ).all()
    )
    return [user_response(user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, _: UserManager, db: DbSession) -> UserResponse:
    if payload.department_id and not await db.get(Department, payload.department_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Department not found")
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        department_id=payload.department_id,
        roles=await assignable_roles(db, payload.role_ids),
        positions=await assignable_positions(db, payload.position_ids),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists") from None
    await db.refresh(user, attribute_names=["roles", "positions"])
    return user_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, payload: UserUpdate, actor: UserManager, db: DbSession
) -> UserResponse:
    user = await db.scalar(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.roles), selectinload(User.positions))
    )
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.is_superuser:
        raise HTTPException(status.HTTP_409_CONFLICT, "Superuser must be managed through handover")
    if user.id == actor.id and payload.enabled is False:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot disable the current user")
    changes = payload.model_dump(exclude_unset=True, exclude={"role_ids", "position_ids"})
    if "department_id" in changes and changes["department_id"]:
        if not await db.get(Department, changes["department_id"]):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Department not found")
    for field, value in changes.items():
        setattr(user, field, value)
    if payload.role_ids is not None:
        user.roles = await assignable_roles(db, payload.role_ids)
    if payload.position_ids is not None:
        user.positions = await assignable_positions(db, payload.position_ids)
    await db.commit()
    return user_response(user)
