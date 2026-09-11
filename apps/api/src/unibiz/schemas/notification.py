from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ChannelCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=100)
    webhook_url: HttpUrl
    signing_secret: str | None = Field(default=None, max_length=256)


class ChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    webhook_url: HttpUrl | None = None
    signing_secret: str | None = Field(default=None, max_length=256)
    enabled: bool | None = None


class ChannelResponse(BaseModel):
    id: UUID
    code: str
    name: str
    channel_type: str
    enabled: bool
    webhook_hint: str
    has_signing_secret: bool


class TemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=100)
    message_type: str = Field(default="text", pattern=r"^(text|post)$")
    title_template: str | None = None
    body_template: str = Field(min_length=1)


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    title_template: str | None = None
    body_template: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    message_type: str
    title_template: str | None
    body_template: str
    enabled: bool


class DeliveryCreate(BaseModel):
    channel_code: str
    template_code: str
    variables: dict[str, str] = {}
    idempotency_key: str = Field(min_length=8, max_length=128)


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    channel_id: UUID
    template_id: UUID
    idempotency_key: str
    status: str
    attempt_count: int
    next_attempt_at: datetime
    last_error: str | None
    sent_at: datetime | None
    created_at: datetime
