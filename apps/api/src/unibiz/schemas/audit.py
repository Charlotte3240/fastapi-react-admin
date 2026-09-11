from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_name: str | None
    action: str
    resource_type: str
    resource_id: str | None
    changes: dict | None
    occurred_at: datetime
    ip_address: str | None


class AuditLogPage(BaseModel):
    items: list[AuditLogResponse]
    total: int
