from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from unibiz.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from unibiz.models.system import Permission

service_account_permissions = Table(
    "service_account_permissions",
    Base.metadata,
    Column(
        "service_account_id",
        ForeignKey("service_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class ServiceAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_accounts"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permissions: Mapped[list[Permission]] = relationship(secondary=service_account_permissions)


class ServiceApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_api_keys"
    service_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_accounts.id", ondelete="CASCADE"), index=True
    )
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
