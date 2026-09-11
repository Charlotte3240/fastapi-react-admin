from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update

from unibiz.api.customers import scoped_query
from unibiz.api.dependencies import DbSession, permission_codes, require_permission
from unibiz.models.crm import Contact, Customer
from unibiz.models.system import User
from unibiz.schemas.crm import ContactCreate, ContactResponse, ContactUpdate

router = APIRouter(prefix="/crm/customers/{customer_id}/contacts", tags=["contacts"])
CustomerViewer = Annotated[User, Depends(require_permission("crm:customer:view"))]
CustomerEditor = Annotated[User, Depends(require_permission("crm:customer:update"))]


def masked_contact(contact: Contact, user: User) -> ContactResponse:
    response = ContactResponse.model_validate(contact)
    if user.is_superuser or "crm:contact:sensitive:view" in permission_codes(user):
        return response
    phone = contact.phone
    if phone and len(phone) >= 7:
        phone = f"{phone[:3]}****{phone[-4:]}"
    email = contact.email
    if email and "@" in email:
        local, domain = email.split("@", 1)
        email = f"{local[:1]}***@{domain}"
    return response.model_copy(update={"phone": phone, "email": email})


async def visible_customer(customer_id: UUID, user: User, db: DbSession) -> Customer:
    customer = await db.scalar(scoped_query(user, "view_scope").where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


async def editable_customer(customer_id: UUID, user: User, db: DbSession) -> Customer:
    customer = await db.scalar(scoped_query(user, "edit_scope").where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found in editable scope")
    return customer


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    customer_id: UUID, user: CustomerViewer, db: DbSession
) -> list[ContactResponse]:
    await visible_customer(customer_id, user, db)
    contacts = list(
        (
            await db.scalars(
                select(Contact)
                .where(Contact.customer_id == customer_id, Contact.deleted_at.is_(None))
                .order_by(Contact.is_primary.desc(), Contact.created_at)
            )
        ).all()
    )
    return [masked_contact(contact, user) for contact in contacts]


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    customer_id: UUID, payload: ContactCreate, user: CustomerEditor, db: DbSession
) -> ContactResponse:
    await editable_customer(customer_id, user, db)
    if payload.is_primary:
        await db.execute(
            update(Contact)
            .where(Contact.customer_id == customer_id, Contact.deleted_at.is_(None))
            .values(is_primary=False)
        )
    contact = Contact(customer_id=customer_id, **payload.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return masked_contact(contact, user)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    customer_id: UUID,
    contact_id: UUID,
    payload: ContactUpdate,
    user: CustomerEditor,
    db: DbSession,
) -> ContactResponse:
    await editable_customer(customer_id, user, db)
    contact = await db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.customer_id == customer_id,
            Contact.deleted_at.is_(None),
        )
    )
    if not contact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    if payload.is_primary:
        await db.execute(
            update(Contact)
            .where(Contact.customer_id == customer_id, Contact.id != contact_id)
            .values(is_primary=False)
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return masked_contact(contact, user)
