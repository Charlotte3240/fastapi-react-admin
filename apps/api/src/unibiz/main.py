import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from unibiz.api.router import api_router
from unibiz.core.audit import record_request_audit
from unibiz.core.config import get_settings
from unibiz.core.database import session_factory
from unibiz.core.http_security import MaximumBodySizeMiddleware
from unibiz.core.permission_catalog import sync_permission_catalog

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with session_factory() as db:
        await sync_permission_catalog(db)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(MaximumBodySizeMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@app.exception_handler(HTTPException)
async def structured_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": detail if isinstance(detail, str) else "Request failed",
            "detail": detail,
            "request_id": request_id(request),
        },
    )


@app.exception_handler(RequestValidationError)
async def structured_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "detail": exc.errors(),
            "request_id": request_id(request),
        },
    )


@app.middleware("http")
async def audit_mutations(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    is_successful_mutation = (
        request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 400
    )
    is_login_attempt = request.url.path == "/api/v1/auth/login"
    if is_successful_mutation or is_login_attempt:
        try:
            await record_request_audit(request, response.status_code)
        except Exception:
            logger.exception("Failed to persist audit log")
    return response


@app.middleware("http")
async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}
