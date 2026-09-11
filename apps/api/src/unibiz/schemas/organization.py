from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    parent_id: UUID | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: UUID | None = None
    enabled: bool | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    parent_id: UUID | None
    enabled: bool


class PositionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")


class PositionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    enabled: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    department_id: UUID | None = None
    role_ids: list[UUID] = []
    position_ids: list[UUID] = []


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: UUID | None = None
    enabled: bool | None = None
    role_ids: list[UUID] | None = None
    position_ids: list[UUID] | None = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    display_name: str
    department_id: UUID | None
    enabled: bool
    is_superuser: bool
    roles: list[dict]
    positions: list[dict]
