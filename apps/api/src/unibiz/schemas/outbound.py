from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ConnectorCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=100)
    base_url: HttpUrl
    auth_type: str = Field(default="none", pattern=r"^(none|bearer|api_key_header)$")
    credential: str | None = Field(default=None, max_length=2000)
    api_key_header: str = Field(default="X-API-Key", max_length=100)
    health_path: str = Field(default="/", max_length=500, pattern=r"^/[^?#]*$")
    timeout_seconds: int = Field(default=10, ge=1, le=30)


class ConnectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    base_url: HttpUrl | None = None
    auth_type: str | None = Field(default=None, pattern=r"^(none|bearer|api_key_header)$")
    credential: str | None = Field(default=None, max_length=2000)
    api_key_header: str | None = Field(default=None, max_length=100)
    health_path: str | None = Field(default=None, max_length=500, pattern=r"^/[^?#]*$")
    timeout_seconds: int | None = Field(default=None, ge=1, le=30)


class ConnectorResponse(BaseModel):
    id: UUID
    code: str
    name: str
    base_url: str
    allowed_host: str
    auth_type: str
    has_credential: bool
    health_path: str
    timeout_seconds: int
    enabled: bool


class CallLogResponse(BaseModel):
    id: UUID
    connector_id: UUID
    operation: str
    method: str
    url_path: str
    status: str
    http_status: int | None
    duration_ms: int | None
    error: str | None
    response_excerpt: str | None
    completed_at: datetime | None
    created_at: datetime


class OutboundTaskCreate(BaseModel):
    connector_code: str = Field(min_length=2, max_length=64)
    operation: str = Field(min_length=1, max_length=100)
    method: str = Field(default="POST", pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    url_path: str = Field(min_length=1, max_length=500, pattern=r"^/(?:[^/?#][^?#]*)?$")
    body: dict | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    max_attempts: int = Field(default=5, ge=1, le=10)


class OutboundTaskResponse(BaseModel):
    id: UUID
    connector_id: UUID
    operation: str
    method: str
    url_path: str
    idempotency_key: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime
    last_error: str | None
    last_http_status: int | None
    completed_at: datetime | None
    created_at: datetime
