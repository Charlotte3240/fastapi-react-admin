from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from jwt import PyJWTError
from unibiz.core.database import session_factory
from unibiz.core.security import decode_access_token
from unibiz.models.system import AuditLog


def _actor_id(request: Request) -> UUID | None:
    state_actor = getattr(request.state, "audit_actor_id", None)
    if state_actor:
        return state_actor
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    try:
        return decode_access_token(authorization.removeprefix("Bearer "))
    except (PyJWTError, ValueError):
        return None


def _resource(request: Request) -> tuple[str, str | None]:
    path_params = request.scope.get("path_params", {})
    resource_id = next(
        (str(value) for key, value in reversed(path_params.items()) if key.endswith("_id")), None
    )
    parts = [part for part in request.url.path.split("/") if part]
    resource_type = parts[-1] if parts else "unknown"
    if resource_id and resource_type == resource_id and len(parts) > 1:
        resource_type = parts[-2]
    return resource_type[:64], resource_id


async def record_request_audit(request: Request, status_code: int) -> None:
    route = request.scope.get("route")
    action = getattr(route, "name", None) or f"{request.method.lower()}_request"
    resource_type, resource_id = _resource(request)
    log = AuditLog(
        actor_id=_actor_id(request),
        action=str(action)[:128],
        resource_type=resource_type,
        resource_id=resource_id,
        changes={"method": request.method, "path": request.url.path, "status_code": status_code},
        occurred_at=datetime.now(UTC),
        ip_address=request.client.host if request.client else None,
    )
    async with session_factory() as db:
        db.add(log)
        await db.commit()
