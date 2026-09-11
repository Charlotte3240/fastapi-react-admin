from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from unibiz.models.crm import CustomerType


class CustomerCreate(BaseModel):
    customer_type: CustomerType
    name: str = Field(min_length=1, max_length=200)
    owner_id: UUID | None = None
    source_system: str | None = Field(default=None, max_length=64)
    external_id: str | None = Field(default=None, max_length=128)
    credit_code: str | None = Field(default=None, max_length=32)
    industry: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    extra_data: dict = {}

    @model_validator(mode="after")
    def paired_external_identity(self) -> "CustomerCreate":
        if bool(self.source_system) != bool(self.external_id):
            raise ValueError("source_system and external_id must be provided together")
        return self


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    credit_code: str | None = Field(default=None, max_length=32)
    industry: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    extra_data: dict | None = None


class CustomerTransfer(BaseModel):
    owner_id: UUID


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_type: str
    name: str
    owner_id: UUID
    owner_department_id: UUID | None
    source_system: str | None
    external_id: str | None
    credit_code: str | None
    industry: str | None
    phone: str | None
    email: str | None
    address: str | None
    status: str | None
    notes: str | None
    extra_data: dict
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int


class ExternalCustomerUpsert(BaseModel):
    customer_type: CustomerType
    name: str = Field(min_length=1, max_length=200)
    owner_id: UUID
    credit_code: str | None = Field(default=None, max_length=32)
    industry: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    extra_data: dict = {}


class ExternalCustomerUpsertResponse(BaseModel):
    created: bool
    customer: CustomerResponse


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    is_primary: bool = False
    notes: str | None = None
    extra_data: dict = {}


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    is_primary: bool | None = None
    notes: str | None = None
    extra_data: dict | None = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: UUID
    name: str
    title: str | None
    phone: str | None
    email: str | None
    is_primary: bool
    notes: str | None
    extra_data: dict
    created_at: datetime
    updated_at: datetime


class FollowUpCreate(BaseModel):
    contact_id: UUID | None = None
    method: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1)
    result: str | None = None
    followed_at: datetime
    next_follow_up_at: datetime | None = None


class FollowUpUpdate(BaseModel):
    contact_id: UUID | None = None
    method: str | None = Field(default=None, min_length=1, max_length=64)
    content: str | None = Field(default=None, min_length=1)
    result: str | None = None
    followed_at: datetime | None = None
    next_follow_up_at: datetime | None = None


class FollowUpVoid(BaseModel):
    reason: str = Field(min_length=1)


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: UUID
    contact_id: UUID | None
    author_id: UUID
    method: str
    content: str
    result: str | None
    followed_at: datetime
    next_follow_up_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    created_at: datetime
    updated_at: datetime
