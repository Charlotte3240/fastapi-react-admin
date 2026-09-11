from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.outbound import OutboundCallLog, OutboundConnector, OutboundTask
from unibiz.models.system import User
from unibiz.schemas.outbound import (
    CallLogResponse,
    ConnectorCreate,
    ConnectorResponse,
    ConnectorUpdate,
    OutboundTaskCreate,
    OutboundTaskResponse,
)
from unibiz.services.outbound import (
    decrypt_credentials,
    encrypt_credentials,
    test_connector,
    validate_public_base_url,
)

router = APIRouter(prefix="/system/outbound", tags=["outbound-connectors"])
Manager = Annotated[User, Depends(require_permission("system:outbound_connector:manage"))]
LogViewer = Annotated[User, Depends(require_permission("system:outbound_call:view"))]


def response_for(connector: OutboundConnector) -> ConnectorResponse:
    return ConnectorResponse(
        id=connector.id,
        code=connector.code,
        name=connector.name,
        base_url=connector.base_url,
        allowed_host=connector.allowed_host,
        auth_type=connector.auth_type,
        has_credential=connector.encrypted_credentials is not None,
        health_path=connector.health_path,
        timeout_seconds=connector.timeout_seconds,
        enabled=connector.enabled,
    )


def validate_auth(auth_type: str, credential: str | None) -> None:
    if auth_type != "none" and not credential:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "credential is required for the selected authentication type",
        )


@router.get("/connectors", response_model=list[ConnectorResponse])
async def list_connectors(_: Manager, db: DbSession) -> list[ConnectorResponse]:
    connectors = list(
        (await db.scalars(select(OutboundConnector).order_by(OutboundConnector.name))).all()
    )
    return [response_for(item) for item in connectors]


@router.post("/connectors", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(
    payload: ConnectorCreate, _: Manager, db: DbSession
) -> ConnectorResponse:
    validate_auth(payload.auth_type, payload.credential)
    try:
        allowed_host = await validate_public_base_url(str(payload.base_url))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    connector = OutboundConnector(
        code=payload.code,
        name=payload.name,
        base_url=str(payload.base_url),
        allowed_host=allowed_host,
        auth_type=payload.auth_type,
        encrypted_credentials=encrypt_credentials(payload.credential, payload.api_key_header),
        health_path=payload.health_path,
        timeout_seconds=payload.timeout_seconds,
    )
    db.add(connector)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Connector code already exists") from None
    await db.refresh(connector)
    return response_for(connector)


@router.patch("/connectors/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: UUID, payload: ConnectorUpdate, _: Manager, db: DbSession
) -> ConnectorResponse:
    connector = await db.get(OutboundConnector, connector_id)
    if not connector:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connector not found")
    if payload.base_url is not None:
        try:
            connector.allowed_host = await validate_public_base_url(str(payload.base_url))
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
        connector.base_url = str(payload.base_url)
    for field in ("name", "enabled", "health_path", "timeout_seconds"):
        if field in payload.model_fields_set:
            setattr(connector, field, getattr(payload, field))
    new_auth_type = payload.auth_type or connector.auth_type
    current = decrypt_credentials(connector.encrypted_credentials)
    credential = (
        payload.credential
        if "credential" in payload.model_fields_set
        else current.get("credential")
    )
    api_key_header = payload.api_key_header or current.get("api_key_header") or "X-API-Key"
    if new_auth_type == "none":
        credential = None
    validate_auth(new_auth_type, credential)
    connector.auth_type = new_auth_type
    connector.encrypted_credentials = encrypt_credentials(credential, str(api_key_header))
    await db.commit()
    await db.refresh(connector)
    return response_for(connector)


@router.post("/connectors/{connector_id}/test", response_model=CallLogResponse)
async def run_connectivity_test(connector_id: UUID, _: Manager, db: DbSession) -> OutboundCallLog:
    connector = await db.get(OutboundConnector, connector_id)
    if not connector or not connector.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enabled connector not found")
    return await test_connector(db, connector)


@router.get("/calls", response_model=list[CallLogResponse])
async def list_call_logs(_: LogViewer, db: DbSession) -> list[OutboundCallLog]:
    return list(
        (
            await db.scalars(
                select(OutboundCallLog).order_by(OutboundCallLog.created_at.desc()).limit(200)
            )
        ).all()
    )


@router.post("/tasks", response_model=OutboundTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_outbound_task(
    payload: OutboundTaskCreate, _: Manager, db: DbSession
) -> OutboundTask:
    connector = await db.scalar(
        select(OutboundConnector).where(
            OutboundConnector.code == payload.connector_code,
            OutboundConnector.enabled.is_(True),
        )
    )
    if not connector:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Connector unavailable")
    task = OutboundTask(
        connector_id=connector.id,
        operation=payload.operation,
        method=payload.method,
        url_path=payload.url_path,
        body=payload.body,
        idempotency_key=payload.idempotency_key,
        max_attempts=payload.max_attempts,
        next_attempt_at=datetime.now(UTC),
    )
    db.add(task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(OutboundTask).where(OutboundTask.idempotency_key == payload.idempotency_key)
        )
        if not existing:
            raise
        return existing
    await db.refresh(task)
    return task


@router.get("/tasks", response_model=list[OutboundTaskResponse])
async def list_outbound_tasks(_: LogViewer, db: DbSession) -> list[OutboundTask]:
    return list(
        (
            await db.scalars(
                select(OutboundTask).order_by(OutboundTask.created_at.desc()).limit(200)
            )
        ).all()
    )


@router.post("/tasks/{task_id}/retry", response_model=OutboundTaskResponse)
async def retry_outbound_task(task_id: UUID, _: Manager, db: DbSession) -> OutboundTask:
    task = await db.get(OutboundTask, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outbound task not found")
    if task.status not in {"failed", "retry"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Outbound task cannot be retried")
    task.status = "retry"
    task.next_attempt_at = datetime.now(UTC)
    task.completed_at = None
    await db.commit()
    await db.refresh(task)
    return task
