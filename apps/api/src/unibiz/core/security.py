from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from unibiz.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise ValueError("Invalid token type")
    return UUID(payload["sub"])


def new_opaque_token() -> tuple[str, str]:
    raw = token_urlsafe(48)
    return raw, sha256(raw.encode()).hexdigest()


def hash_token(raw: str) -> str:
    return sha256(raw.encode()).hexdigest()


def new_api_key() -> tuple[str, str, str]:
    prefix = token_urlsafe(6).replace("-", "").replace("_", "")[:8]
    raw = f"ubk_{prefix}_{token_urlsafe(32)}"
    return raw, prefix, hash_token(raw)
