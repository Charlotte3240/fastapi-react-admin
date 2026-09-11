from fastapi import APIRouter

from unibiz.api.audit import router as audit_router
from unibiz.api.auth import router as auth_router
from unibiz.api.bootstrap import router as bootstrap_router
from unibiz.api.contacts import router as contacts_router
from unibiz.api.customers import router as customers_router
from unibiz.api.follow_ups import router as follow_ups_router
from unibiz.api.integration_crm import router as integration_crm_router
from unibiz.api.notifications import router as notifications_router
from unibiz.api.organization import router as organization_router
from unibiz.api.outbound import router as outbound_router
from unibiz.api.roles import router as roles_router
from unibiz.api.service_accounts import router as service_accounts_router
from unibiz.api.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(bootstrap_router)
api_router.include_router(roles_router)
api_router.include_router(customers_router)
api_router.include_router(contacts_router)
api_router.include_router(follow_ups_router)
api_router.include_router(organization_router)
api_router.include_router(users_router)
api_router.include_router(notifications_router)
api_router.include_router(audit_router)
api_router.include_router(service_accounts_router)
api_router.include_router(integration_crm_router)
api_router.include_router(outbound_router)
