from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from unibiz.api.dependencies import (
    DbSession,
    effective_scope,
    permission_codes,
    require_permission,
)
from unibiz.models.crm import Customer
from unibiz.models.system import User
from unibiz.schemas.crm import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerTransfer,
    CustomerUpdate,
)

router = APIRouter(prefix="/crm/customers", tags=["customers"])
CustomerViewer = Annotated[User, Depends(require_permission("crm:customer:view"))]
CustomerCreator = Annotated[User, Depends(require_permission("crm:customer:create"))]
CustomerEditor = Annotated[User, Depends(require_permission("crm:customer:update"))]
CustomerTransferer = Annotated[User, Depends(require_permission("crm:customer:transfer"))]


def scoped_query(user: User, scope_attribute: str):
    query = select(Customer).where(Customer.deleted_at.is_(None))
    scope = effective_scope(user, scope_attribute)
    if scope == "self":
        query = query.where(Customer.owner_id == user.id)
    elif scope == "department":
        query = query.where(Customer.owner_department_id == user.department_id)
    return query


def masked_customer(customer: Customer, user: User) -> CustomerResponse:
    response = CustomerResponse.model_validate(customer)
    if user.is_superuser or "crm:contact:sensitive:view" in permission_codes(user):
        return response
    phone = customer.phone
    if phone and len(phone) >= 7:
        phone = f"{phone[:3]}****{phone[-4:]}"
    email = customer.email
    if email and "@" in email:
        local, domain = email.split("@", 1)
        email = f"{local[:1]}***@{domain}"
    return response.model_copy(update={"phone": phone, "email": email})


async def editable_customer(customer_id: UUID, user: User, db: DbSession) -> Customer:
    customer = await db.scalar(scoped_query(user, "edit_scope").where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found in editable scope")
    return customer


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    user: CustomerViewer,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=100),
) -> CustomerListResponse:
    query = scoped_query(user, "view_scope")
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(or_(Customer.name.ilike(pattern), Customer.credit_code.ilike(pattern)))
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = int(await db.scalar(count_query) or 0)
    customers = list(
        (
            await db.scalars(
                query.order_by(Customer.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return CustomerListResponse(
        items=[masked_customer(item, user) for item in customers], total=total
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate, user: CustomerCreator, db: DbSession
) -> CustomerResponse:
    owner_id = payload.owner_id or user.id
    if (
        owner_id != user.id
        and not user.is_superuser
        and "crm:customer:transfer" not in permission_codes(user)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot assign another owner")
    owner = await db.get(User, owner_id)
    if not owner or not owner.enabled or owner.deleted_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Owner is unavailable")
    values = payload.model_dump(exclude={"owner_id"})
    customer = Customer(**values, owner_id=owner.id, owner_department_id=owner.department_id)
    db.add(customer)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "External customer already exists") from None
    await db.refresh(customer)
    return masked_customer(customer, user)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: UUID, user: CustomerViewer, db: DbSession) -> CustomerResponse:
    customer = await db.scalar(scoped_query(user, "view_scope").where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return masked_customer(customer, user)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID, payload: CustomerUpdate, user: CustomerEditor, db: DbSession
) -> CustomerResponse:
    customer = await editable_customer(customer_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return masked_customer(customer, user)


@router.post("/{customer_id}/transfer", response_model=CustomerResponse)
async def transfer_customer(
    customer_id: UUID, payload: CustomerTransfer, user: CustomerTransferer, db: DbSession
) -> CustomerResponse:
    customer = await db.scalar(scoped_query(user, "edit_scope").where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found in editable scope")
    owner = await db.get(User, payload.owner_id)
    if not owner or not owner.enabled or owner.deleted_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Owner is unavailable")
    customer.owner_id = owner.id
    customer.owner_department_id = owner.department_id
    await db.commit()
    await db.refresh(customer)
    return masked_customer(customer, user)
