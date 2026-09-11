from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from unibiz.api.dependencies import DbSession, require_permission
from unibiz.core.security import hash_password, new_api_key
from unibiz.models.integration import ServiceAccount, ServiceApiKey
from unibiz.models.system import Permission, User
from unibiz.schemas.service_account import (
    RotatedKeyResponse,
    RotateKeyRequest,
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceAccountResponse,
    ServiceAccountUpdate,
)

router = APIRouter(prefix="/system/service-accounts", tags=["service-accounts"])
Manager = Annotated[User, Depends(require_permission("system:service_account:manage"))]


async def permissions_from_codes(db: DbSession, codes: list[str]) -> list[Permission]:
    permissions = list(
        (await db.scalars(select(Permission).where(Permission.code.in_(codes)))).all()
    )
    missing = set(codes) - {item.code for item in permissions}
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unknown permissions: {', '.join(sorted(missing))}",
        )
    return permissions


async def response_for(db: DbSession, account: ServiceAccount) -> ServiceAccountResponse:
    prefixes = list(
        (
            await db.scalars(
                select(ServiceApiKey.key_prefix).where(
                    ServiceApiKey.service_account_id == account.id,
                    ServiceApiKey.revoked_at.is_(None),
                )
            )
        ).all()
    )
    return ServiceAccountResponse(
        id=account.id,
        code=account.code,
        name=account.name,
        enabled=account.enabled,
        permission_codes=sorted(item.code for item in account.permissions),
        expires_at=account.expires_at,
        last_used_at=account.last_used_at,
        active_key_prefixes=prefixes,
    )


@router.get("", response_model=list[ServiceAccountResponse])
async def list_service_accounts(_: Manager, db: DbSession) -> list[ServiceAccountResponse]:
    accounts = list(
        (
            await db.scalars(
                select(ServiceAccount)
                .options(selectinload(ServiceAccount.permissions))
                .order_by(ServiceAccount.name)
            )
        ).all()
    )
    return [await response_for(db, account) for account in accounts]


@router.post("", response_model=ServiceAccountCreated, status_code=status.HTTP_201_CREATED)
async def create_service_account(
    payload: ServiceAccountCreate, _: Manager, db: DbSession
) -> ServiceAccountCreated:
    user = User(
        username=f"svc__{payload.code}",
        display_name=f"服务账号：{payload.name}",
        password_hash=hash_password(str(uuid4())),
        enabled=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    account = ServiceAccount(
        user_id=user.id,
        code=payload.code,
        name=payload.name,
        expires_at=payload.expires_at,
        permissions=await permissions_from_codes(db, payload.permission_codes),
    )
    db.add(account)
    await db.flush()
    raw, prefix, secret_hash = new_api_key()
    db.add(
        ServiceApiKey(
            service_account_id=account.id,
            key_prefix=prefix,
            secret_hash=secret_hash,
            expires_at=payload.key_expires_at,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Service account code already exists"
        ) from None
    await db.refresh(account, attribute_names=["permissions"])
    base = await response_for(db, account)
    return ServiceAccountCreated(**base.model_dump(), api_key=raw)


@router.patch("/{account_id}", response_model=ServiceAccountResponse)
async def update_service_account(
    account_id: UUID, payload: ServiceAccountUpdate, _: Manager, db: DbSession
) -> ServiceAccountResponse:
    account = await db.scalar(
        select(ServiceAccount)
        .where(ServiceAccount.id == account_id)
        .options(selectinload(ServiceAccount.permissions))
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service account not found")
    for field in ("name", "enabled", "expires_at"):
        if field in payload.model_fields_set:
            setattr(account, field, getattr(payload, field))
    if payload.permission_codes is not None:
        account.permissions = await permissions_from_codes(db, payload.permission_codes)
    await db.commit()
    return await response_for(db, account)


@router.post("/{account_id}/rotate-key", response_model=RotatedKeyResponse)
async def rotate_service_key(
    account_id: UUID, payload: RotateKeyRequest, _: Manager, db: DbSession
) -> RotatedKeyResponse:
    account = await db.get(ServiceAccount, account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service account not found")
    if payload.revoke_existing:
        await db.execute(
            update(ServiceApiKey)
            .where(
                ServiceApiKey.service_account_id == account_id, ServiceApiKey.revoked_at.is_(None)
            )
            .values(revoked_at=datetime.now(UTC))
        )
    raw, prefix, secret_hash = new_api_key()
    db.add(
        ServiceApiKey(
            service_account_id=account.id,
            key_prefix=prefix,
            secret_hash=secret_hash,
            expires_at=payload.expires_at,
        )
    )
    await db.commit()
    return RotatedKeyResponse(api_key=raw, key_prefix=prefix)
