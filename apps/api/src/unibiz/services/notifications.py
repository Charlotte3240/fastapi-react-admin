import base64
import hashlib
import hmac
import json
import re
import time
from datetime import UTC, datetime, timedelta
from string import Template
from urllib.parse import urlparse

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unibiz.core.config import get_settings
from unibiz.models.notification import (
    NotificationChannel,
    NotificationDelivery,
    NotificationTemplate,
)


def validate_feishu_webhook(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "open.feishu.cn"
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or re.fullmatch(r"/open-apis/bot/v2/hook/[A-Za-z0-9_-]+", parsed.path) is None
    ):
        raise ValueError("Only Feishu custom bot HTTPS webhooks are allowed")


def encrypt_channel_config(webhook_url: str, signing_secret: str | None) -> str:
    validate_feishu_webhook(webhook_url)
    payload = json.dumps({"webhook_url": webhook_url, "signing_secret": signing_secret})
    return Fernet(get_settings().webhook_encryption_key.encode()).encrypt(payload.encode()).decode()


def decrypt_channel_config(encrypted: str) -> dict[str, str | None]:
    raw = Fernet(get_settings().webhook_encryption_key.encode()).decrypt(encrypted.encode())
    return json.loads(raw)


def channel_summary(channel: NotificationChannel) -> tuple[str, bool]:
    config = decrypt_channel_config(channel.encrypted_config)
    webhook = str(config["webhook_url"])
    return f"{webhook[:38]}…{webhook[-6:]}", bool(config.get("signing_secret"))


def render_message(template: NotificationTemplate, variables: dict[str, str]) -> dict:
    body = Template(template.body_template).safe_substitute(variables)
    if template.message_type == "post":
        title = Template(template.title_template or "通知").safe_substitute(variables)
        return {
            "msg_type": "post",
            "content": {
                "post": {"zh_cn": {"title": title, "content": [[{"tag": "text", "text": body}]]}}
            },
        }
    return {"msg_type": "text", "content": {"text": body}}


def add_signature(payload: dict, secret: str | None) -> None:
    if not secret:
        return
    timestamp = int(time.time())
    string_to_sign = f"{timestamp}\n{secret}"
    signature = hmac.new(string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    payload["timestamp"] = str(timestamp)
    payload["sign"] = base64.b64encode(signature).decode()


async def process_one_delivery(db: AsyncSession) -> bool:
    now = datetime.now(UTC)
    delivery = await db.scalar(
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status.in_(["pending", "retry"]),
            NotificationDelivery.next_attempt_at <= now,
        )
        .order_by(NotificationDelivery.next_attempt_at)
        .with_for_update(skip_locked=True)
    )
    if not delivery:
        return False
    delivery.status = "sending"
    delivery.attempt_count += 1
    await db.commit()

    try:
        channel = await db.get(NotificationChannel, delivery.channel_id)
        template = await db.get(NotificationTemplate, delivery.template_id)
        if not channel or not template or not channel.enabled or not template.enabled:
            raise RuntimeError("Channel or template is unavailable")
        config = decrypt_channel_config(channel.encrypted_config)
        webhook_url = str(config["webhook_url"])
        validate_feishu_webhook(webhook_url)
        payload = render_message(template, delivery.variables)
        add_signature(payload, config.get("signing_secret"))
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("code") != 0:
                raise RuntimeError(f"Feishu error {result.get('code')}: {result.get('msg')}")
        delivery.status = "sent"
        delivery.sent_at = datetime.now(UTC)
        delivery.last_error = None
    except Exception as exc:
        delivery.last_error = str(exc)[:2000]
        if delivery.attempt_count >= 5:
            delivery.status = "failed"
        else:
            delivery.status = "retry"
            delivery.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=min(30 * (2 ** (delivery.attempt_count - 1)), 1800)
            )
    await db.commit()
    return True
