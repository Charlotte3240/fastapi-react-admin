from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from unibiz.api.customers import scoped_query
from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.crm import Contact, Customer, FollowUp
from unibiz.models.system import User
from unibiz.schemas.crm import FollowUpCreate, FollowUpResponse, FollowUpUpdate, FollowUpVoid

router = APIRouter(prefix="/crm/customers/{customer_id}/follow-ups", tags=["follow-ups"])
CustomerViewer = Annotated[User, Depends(require_permission("crm:customer:view"))]
FollowUpCreator = Annotated[User, Depends(require_permission("crm:follow_up:create"))]
FollowUpVoider = Annotated[User, Depends(require_permission("crm:follow_up:void"))]


async def ensure_contact(customer_id: UUID, contact_id: UUID | None, db: DbSession) -> None:
    if contact_id and not await db.scalar(
        select(Contact.id).where(
            Contact.id == contact_id,
            Contact.customer_id == customer_id,
            Contact.deleted_at.is_(None),
        )
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Contact does not belong to customer"
        )


@router.get("", response_model=list[FollowUpResponse])
async def list_follow_ups(customer_id: UUID, user: CustomerViewer, db: DbSession) -> list[FollowUp]:
    if not await db.scalar(scoped_query(user, "view_scope").where(Customer.id == customer_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return list(
        (
            await db.scalars(
                select(FollowUp)
                .where(FollowUp.customer_id == customer_id)
                .order_by(FollowUp.followed_at.desc())
            )
        ).all()
    )


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
async def create_follow_up(
    customer_id: UUID, payload: FollowUpCreate, user: FollowUpCreator, db: DbSession
) -> FollowUp:
    if not await db.scalar(scoped_query(user, "edit_scope").where(Customer.id == customer_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found in editable scope")
    await ensure_contact(customer_id, payload.contact_id, db)
    follow_up = FollowUp(customer_id=customer_id, author_id=user.id, **payload.model_dump())
    db.add(follow_up)
    await db.commit()
    await db.refresh(follow_up)
    return follow_up


@router.patch("/{follow_up_id}", response_model=FollowUpResponse)
async def update_follow_up(
    customer_id: UUID,
    follow_up_id: UUID,
    payload: FollowUpUpdate,
    user: FollowUpCreator,
    db: DbSession,
) -> FollowUp:
    follow_up = await db.scalar(
        select(FollowUp).where(FollowUp.id == follow_up_id, FollowUp.customer_id == customer_id)
    )
    if not follow_up:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Follow-up not found")
    if follow_up.author_id != user.id or follow_up.created_at < datetime.now(UTC) - timedelta(
        hours=24
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Follow-up edit window has closed")
    if follow_up.voided_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Voided follow-up cannot be edited")
    if "contact_id" in payload.model_fields_set:
        await ensure_contact(customer_id, payload.contact_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(follow_up, field, value)
    await db.commit()
    await db.refresh(follow_up)
    return follow_up


@router.post("/{follow_up_id}/void", response_model=FollowUpResponse)
async def void_follow_up(
    customer_id: UUID,
    follow_up_id: UUID,
    payload: FollowUpVoid,
    _: FollowUpVoider,
    db: DbSession,
) -> FollowUp:
    follow_up = await db.scalar(
        select(FollowUp).where(FollowUp.id == follow_up_id, FollowUp.customer_id == customer_id)
    )
    if not follow_up:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Follow-up not found")
    if follow_up.voided_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Follow-up is already voided")
    follow_up.voided_at = datetime.now(UTC)
    follow_up.void_reason = payload.reason
    await db.commit()
    await db.refresh(follow_up)
    return follow_up
