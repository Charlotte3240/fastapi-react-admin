from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.system import Department, Position, User
from unibiz.schemas.organization import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
)

router = APIRouter(prefix="/system", tags=["organization"])
UserViewer = Annotated[User, Depends(require_permission("system:user:view"))]
UserManager = Annotated[User, Depends(require_permission("system:user:manage"))]


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(_: UserViewer, db: DbSession) -> list[Department]:
    return list((await db.scalars(select(Department).order_by(Department.name))).all())


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(payload: DepartmentCreate, _: UserManager, db: DbSession) -> Department:
    if payload.parent_id and not await db.get(Department, payload.parent_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Parent department not found")
    department = Department(**payload.model_dump())
    db.add(department)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Department code already exists") from None
    await db.refresh(department)
    return department


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID, payload: DepartmentUpdate, _: UserManager, db: DbSession
) -> Department:
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")
    if payload.parent_id == department_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Department cannot parent itself"
        )
    if payload.parent_id and not await db.get(Department, payload.parent_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Parent department not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(department, field, value)
    await db.commit()
    await db.refresh(department)
    return department


@router.get("/positions", response_model=list[PositionResponse])
async def list_positions(_: UserViewer, db: DbSession) -> list[Position]:
    return list((await db.scalars(select(Position).order_by(Position.name))).all())


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(payload: PositionCreate, _: UserManager, db: DbSession) -> Position:
    position = Position(**payload.model_dump())
    db.add(position)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Position code already exists") from None
    await db.refresh(position)
    return position


@router.patch("/positions/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: UUID, payload: PositionUpdate, _: UserManager, db: DbSession
) -> Position:
    position = await db.get(Position, position_id)
    if not position:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(position, field, value)
    await db.commit()
    await db.refresh(position)
    return position
