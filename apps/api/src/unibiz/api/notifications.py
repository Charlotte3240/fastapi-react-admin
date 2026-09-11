from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.notification import (
    NotificationChannel,
    NotificationDelivery,
    NotificationTemplate,
)
from unibiz.models.system import User
from unibiz.schemas.notification import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    DeliveryCreate,
    DeliveryResponse,
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)
from unibiz.services.notifications import (
    channel_summary,
    decrypt_channel_config,
    encrypt_channel_config,
)

router = APIRouter(prefix="/system/notifications", tags=["notifications"])
ChannelManager = Annotated[User, Depends(require_permission("notify:channel:manage"))]
DeliveryViewer = Annotated[User, Depends(require_permission("notify:delivery:view"))]


def channel_response(channel: NotificationChannel) -> ChannelResponse:
    hint, has_secret = channel_summary(channel)
    return ChannelResponse(
        id=channel.id,
        code=channel.code,
        name=channel.name,
        channel_type=channel.channel_type,
        enabled=channel.enabled,
        webhook_hint=hint,
        has_signing_secret=has_secret,
    )


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(_: ChannelManager, db: DbSession) -> list[ChannelResponse]:
    channels = list(
        (await db.scalars(select(NotificationChannel).order_by(NotificationChannel.name))).all()
    )
    return [channel_response(channel) for channel in channels]


@router.post("/channels", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    payload: ChannelCreate, _: ChannelManager, db: DbSession
) -> ChannelResponse:
    try:
        encrypted = encrypt_channel_config(str(payload.webhook_url), payload.signing_secret)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    channel = NotificationChannel(code=payload.code, name=payload.name, encrypted_config=encrypted)
    db.add(channel)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Channel code already exists") from None
    await db.refresh(channel)
    return channel_response(channel)


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: UUID, payload: ChannelUpdate, _: ChannelManager, db: DbSession
) -> ChannelResponse:
    channel = await db.get(NotificationChannel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")
    if payload.name is not None:
        channel.name = payload.name
    if payload.enabled is not None:
        channel.enabled = payload.enabled
    update_fields = payload.model_fields_set
    if "webhook_url" in update_fields or "signing_secret" in update_fields:
        current = decrypt_channel_config(channel.encrypted_config)
        webhook_url = str(payload.webhook_url or current["webhook_url"])
        signing_secret = (
            payload.signing_secret
            if "signing_secret" in update_fields
            else current.get("signing_secret")
        )
        try:
            channel.encrypted_config = encrypt_channel_config(webhook_url, signing_secret or None)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    await db.commit()
    await db.refresh(channel)
    return channel_response(channel)


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(_: ChannelManager, db: DbSession) -> list[NotificationTemplate]:
    return list(
        (await db.scalars(select(NotificationTemplate).order_by(NotificationTemplate.name))).all()
    )


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate, _: ChannelManager, db: DbSession
) -> NotificationTemplate:
    template = NotificationTemplate(**payload.model_dump())
    db.add(template)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Template code already exists") from None
    await db.refresh(template)
    return template


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID, payload: TemplateUpdate, _: ChannelManager, db: DbSession
) -> NotificationTemplate:
    template = await db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return template


@router.post("/deliveries", response_model=DeliveryResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_delivery(
    payload: DeliveryCreate, _: ChannelManager, db: DbSession
) -> NotificationDelivery:
    channel = await db.scalar(
        select(NotificationChannel).where(
            NotificationChannel.code == payload.channel_code, NotificationChannel.enabled.is_(True)
        )
    )
    template = await db.scalar(
        select(NotificationTemplate).where(
            NotificationTemplate.code == payload.template_code,
            NotificationTemplate.enabled.is_(True),
        )
    )
    if not channel or not template:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Channel or template unavailable"
        )
    delivery = NotificationDelivery(
        channel_id=channel.id,
        template_id=template.id,
        idempotency_key=payload.idempotency_key,
        variables=payload.variables,
        next_attempt_at=datetime.now(UTC),
    )
    db.add(delivery)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.idempotency_key == payload.idempotency_key
            )
        )
        if not existing:
            raise
        return existing
    await db.refresh(delivery)
    return delivery


@router.get("/deliveries", response_model=list[DeliveryResponse])
async def list_deliveries(_: DeliveryViewer, db: DbSession) -> list[NotificationDelivery]:
    return list(
        (
            await db.scalars(
                select(NotificationDelivery)
                .order_by(NotificationDelivery.created_at.desc())
                .limit(200)
            )
        ).all()
    )


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryResponse)
async def retry_delivery(
    delivery_id: UUID, _: ChannelManager, db: DbSession
) -> NotificationDelivery:
    delivery = await db.get(NotificationDelivery, delivery_id)
    if not delivery:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Delivery not found")
    if delivery.status not in {"failed", "retry"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Delivery cannot be retried")
    delivery.status = "retry"
    delivery.next_attempt_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(delivery)
    return delivery
