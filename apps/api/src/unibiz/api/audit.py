from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, func, select

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.system import AuditLog, User
from unibiz.schemas.audit import AuditLogPage, AuditLogResponse

router = APIRouter(prefix="/system/audit-logs", tags=["audit"])
AuditViewer = Annotated[User, Depends(require_permission("audit:log:view"))]


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    _: AuditViewer,
    db: DbSession,
    action: str | None = None,
    resource_type: str | None = None,
    actor_id: UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditLogPage:
    filters: list[ColumnElement[bool]] = []
    if action:
        filters.append(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if actor_id:
        filters.append(AuditLog.actor_id == actor_id)
    if occurred_from:
        filters.append(AuditLog.occurred_at >= occurred_from)
    if occurred_to:
        filters.append(AuditLog.occurred_at <= occurred_to)

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    rows = (
        await db.execute(
            select(AuditLog, User.display_name)
            .outerjoin(User, User.id == AuditLog.actor_id)
            .where(*filters)
            .order_by(AuditLog.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return AuditLogPage(
        total=total,
        items=[
            AuditLogResponse(
                id=log.id,
                actor_id=log.actor_id,
                actor_name=actor_name,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                changes=log.changes,
                occurred_at=log.occurred_at,
                ip_address=log.ip_address,
            )
            for log, actor_name in rows
        ],
    )
