from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceAccountCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=100)
    permission_codes: list[str] = []
    expires_at: datetime | None = None
    key_expires_at: datetime | None = None


class ServiceAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    permission_codes: list[str] | None = None
    enabled: bool | None = None
    expires_at: datetime | None = None


class ServiceAccountResponse(BaseModel):
    id: UUID
    code: str
    name: str
    enabled: bool
    permission_codes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    active_key_prefixes: list[str]


class ServiceAccountCreated(ServiceAccountResponse):
    api_key: str


class RotateKeyRequest(BaseModel):
    expires_at: datetime | None = None
    revoke_existing: bool = True


class RotatedKeyResponse(BaseModel):
    api_key: str
    key_prefix: str
