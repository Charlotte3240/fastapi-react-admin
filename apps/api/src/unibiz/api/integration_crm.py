from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from unibiz.api.customers import masked_customer, scoped_query
from unibiz.api.dependencies import DbSession, require_permission
from unibiz.models.crm import Customer
from unibiz.models.system import User
from unibiz.schemas.crm import (
    CustomerResponse,
    ExternalCustomerUpsert,
    ExternalCustomerUpsertResponse,
)

router = APIRouter(prefix="/integrations/crm/customers", tags=["integration-crm"])
ExternalWriter = Annotated[User, Depends(require_permission("crm:customer:external:upsert"))]
CustomerViewer = Annotated[User, Depends(require_permission("crm:customer:view"))]


@router.put(
    "/{source_system}/{external_id}",
    response_model=ExternalCustomerUpsertResponse,
)
async def upsert_external_customer(
    payload: ExternalCustomerUpsert,
    user: ExternalWriter,
    db: DbSession,
    source_system: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    external_id: str = Path(min_length=1, max_length=128),
) -> ExternalCustomerUpsertResponse:
    owner = await db.get(User, payload.owner_id)
    if not owner or not owner.enabled or owner.deleted_at or owner.username.startswith("svc__"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "owner_id must reference an enabled human user",
        )

    existing = await db.scalar(
        select(Customer.id).where(
            Customer.source_system == source_system,
            Customer.external_id == external_id,
        )
    )
    values = payload.model_dump(exclude={"owner_id"}) | {
        "source_system": source_system,
        "external_id": external_id,
        "owner_id": owner.id,
        "owner_department_id": owner.department_id,
        "deleted_at": None,
    }
    statement = (
        insert(Customer)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[Customer.source_system, Customer.external_id],
            set_={
                **{
                    key: value
                    for key, value in values.items()
                    if key not in {"source_system", "external_id"}
                },
                "updated_at": datetime.now(UTC),
            },
        )
        .returning(Customer)
    )
    customer = (await db.scalars(statement)).one()
    await db.commit()
    return ExternalCustomerUpsertResponse(
        created=existing is None,
        customer=masked_customer(customer, user),
    )


@router.get("/{source_system}/{external_id}", response_model=CustomerResponse)
async def get_external_customer(
    user: CustomerViewer,
    db: DbSession,
    source_system: str = Path(min_length=1, max_length=64),
    external_id: str = Path(min_length=1, max_length=128),
) -> CustomerResponse:
    customer = await db.scalar(
        scoped_query(user, "view_scope").where(
            Customer.source_system == source_system,
            Customer.external_id == external_id,
        )
    )
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "External customer not found")
    return masked_customer(customer, user)
