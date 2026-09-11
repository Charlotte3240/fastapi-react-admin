from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from unibiz.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutboundConnector(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbound_connectors"
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[str] = mapped_column(String(500))
    allowed_host: Mapped[str] = mapped_column(String(253))
    auth_type: Mapped[str] = mapped_column(String(32), default="none")
    encrypted_credentials: Mapped[str | None] = mapped_column(Text)
    health_path: Mapped[str] = mapped_column(String(500), default="/")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    enabled: Mapped[bool] = mapped_column(default=True)


class OutboundCallLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbound_call_logs"
    connector_id: Mapped[UUID] = mapped_column(
        ForeignKey("outbound_connectors.id", ondelete="CASCADE"), index=True
    )
    operation: Mapped[str] = mapped_column(String(100), index=True)
    method: Mapped[str] = mapped_column(String(16))
    url_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    response_excerpt: Mapped[str | None] = mapped_column(Text)
    request_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboundTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbound_tasks"
    __table_args__ = (UniqueConstraint("idempotency_key"),)
    connector_id: Mapped[UUID] = mapped_column(
        ForeignKey("outbound_connectors.id", ondelete="CASCADE"), index=True
    )
    operation: Mapped[str] = mapped_column(String(100), index=True)
    method: Mapped[str] = mapped_column(String(16))
    url_path: Mapped[str] = mapped_column(String(500))
    body: Mapped[dict | None] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_http_status: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
