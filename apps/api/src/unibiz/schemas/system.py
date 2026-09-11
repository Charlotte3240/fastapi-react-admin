from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from unibiz.models.system import DataScope


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    module: str
    description: str | None


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    view_scope: DataScope = DataScope.SELF
    edit_scope: DataScope = DataScope.SELF
    permission_codes: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    view_scope: DataScope | None = None
    edit_scope: DataScope | None = None
    permission_codes: list[str] | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    is_system: bool
    enabled: bool
    view_scope: str
    edit_scope: str
    permissions: list[PermissionResponse]
