import asyncio
import ipaddress
import json
import socket
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlparse

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unibiz.core.config import get_settings
from unibiz.models.outbound import OutboundCallLog, OutboundConnector, OutboundTask


def encrypt_credentials(credential: str | None, api_key_header: str) -> str | None:
    if credential is None:
        return None
    payload = json.dumps({"credential": credential, "api_key_header": api_key_header})
    return Fernet(get_settings().webhook_encryption_key.encode()).encrypt(payload.encode()).decode()


def decrypt_credentials(encrypted: str | None) -> dict[str, str | None]:
    if not encrypted:
        return {"credential": None, "api_key_header": None}
    raw = Fernet(get_settings().webhook_encryption_key.encode()).decrypt(encrypted.encode())
    return json.loads(raw)


def _public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return address.is_global


async def validate_public_base_url(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only public HTTPS URLs on port 443 are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Local and private network addresses are forbidden")
    try:
        literal_address = ipaddress.ip_address(host)
    except ValueError:
        try:
            results = await asyncio.get_running_loop().getaddrinfo(
                host, 443, type=socket.SOCK_STREAM
            )
        except socket.gaierror:
            raise ValueError("Connector hostname cannot be resolved") from None
        addresses = {item[4][0] for item in results}
        if not addresses or not all(_public_ip(item) for item in addresses):
            raise ValueError("Hostname resolves to a local or private network address") from None
    else:
        if not literal_address.is_global:
            raise ValueError("Local and private network addresses are forbidden")
    return host


async def test_connector(db: AsyncSession, connector: OutboundConnector) -> OutboundCallLog:
    started = time.monotonic()
    log = OutboundCallLog(
        connector_id=connector.id,
        operation="connectivity_test",
        method="GET",
        url_path=connector.health_path,
        status="running",
        request_metadata={},
    )
    db.add(log)
    await db.flush()
    try:
        host = await validate_public_base_url(connector.base_url)
        if host != connector.allowed_host:
            raise RuntimeError("Connector host no longer matches its allowlist")
        config = decrypt_credentials(connector.encrypted_credentials)
        headers: dict[str, str] = {}
        credential = config.get("credential")
        if connector.auth_type == "bearer" and credential:
            headers["Authorization"] = f"Bearer {credential}"
        elif connector.auth_type == "api_key_header" and credential:
            headers[str(config.get("api_key_header") or "X-API-Key")] = credential
        url = urljoin(connector.base_url.rstrip("/") + "/", connector.health_path.lstrip("/"))
        async with httpx.AsyncClient(
            timeout=connector.timeout_seconds, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.get(url, headers=headers)
        log.http_status = response.status_code
        log.response_excerpt = response.text[:1000]
        log.status = "success" if response.is_success else "failed"
        if not response.is_success:
            log.error = f"HTTP {response.status_code}"
    except Exception as exc:
        log.status = "failed"
        log.error = str(exc)[:2000]
    log.duration_ms = int((time.monotonic() - started) * 1000)
    log.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(log)
    return log


def authentication_headers(connector: OutboundConnector) -> dict[str, str]:
    config = decrypt_credentials(connector.encrypted_credentials)
    credential = config.get("credential")
    if connector.auth_type == "bearer" and credential:
        return {"Authorization": f"Bearer {credential}"}
    if connector.auth_type == "api_key_header" and credential:
        return {str(config.get("api_key_header") or "X-API-Key"): credential}
    return {}


async def process_one_outbound_task(db: AsyncSession) -> bool:
    now = datetime.now(UTC)
    task = await db.scalar(
        select(OutboundTask)
        .where(
            OutboundTask.status.in_(["pending", "retry"]),
            OutboundTask.next_attempt_at <= now,
        )
        .order_by(OutboundTask.next_attempt_at)
        .with_for_update(skip_locked=True)
    )
    if not task:
        return False
    task.status = "sending"
    task.attempt_count += 1
    await db.commit()

    connector = await db.get(OutboundConnector, task.connector_id)
    started = time.monotonic()
    log = OutboundCallLog(
        connector_id=task.connector_id,
        operation=task.operation,
        method=task.method,
        url_path=task.url_path,
        status="running",
        request_metadata={"task_id": str(task.id), "attempt": task.attempt_count},
    )
    db.add(log)
    try:
        if not connector or not connector.enabled:
            raise RuntimeError("Connector is unavailable")
        host = await validate_public_base_url(connector.base_url)
        if host != connector.allowed_host:
            raise RuntimeError("Connector host no longer matches its allowlist")
        url = urljoin(connector.base_url.rstrip("/") + "/", task.url_path.lstrip("/"))
        headers = authentication_headers(connector) | {"Idempotency-Key": task.idempotency_key}
        async with httpx.AsyncClient(
            timeout=connector.timeout_seconds, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.request(task.method, url, headers=headers, json=task.body)
        task.last_http_status = response.status_code
        log.http_status = response.status_code
        log.response_excerpt = response.text[:1000]
        if response.is_success:
            task.status = "succeeded"
            task.completed_at = datetime.now(UTC)
            task.last_error = None
            log.status = "success"
        elif response.status_code == 429 or response.status_code >= 500:
            raise RuntimeError(f"Retryable HTTP {response.status_code}")
        else:
            task.status = "failed"
            task.completed_at = datetime.now(UTC)
            task.last_error = f"HTTP {response.status_code}"
            log.status = "failed"
            log.error = task.last_error
    except Exception as exc:
        task.last_error = str(exc)[:2000]
        log.status = "failed"
        log.error = task.last_error
        if task.attempt_count >= task.max_attempts:
            task.status = "failed"
            task.completed_at = datetime.now(UTC)
        else:
            task.status = "retry"
            task.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=min(30 * (2 ** (task.attempt_count - 1)), 1800)
            )
    log.duration_ms = int((time.monotonic() - started) * 1000)
    log.completed_at = datetime.now(UTC)
    await db.commit()
    return True
