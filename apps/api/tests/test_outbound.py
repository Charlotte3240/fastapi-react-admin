import pytest
from unibiz.services.outbound import (
    decrypt_credentials,
    encrypt_credentials,
    validate_public_base_url,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost",
        "https://127.0.0.1",
        "https://10.0.0.1",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]",
        "https://example.com:8443",
        "https://user:password@example.com",
    ],
)
async def test_rejects_unsafe_outbound_urls(url: str) -> None:
    with pytest.raises(ValueError):
        await validate_public_base_url(url)


@pytest.mark.asyncio
async def test_accepts_public_https_ip() -> None:
    assert await validate_public_base_url("https://8.8.8.8/api") == "8.8.8.8"


def test_outbound_credentials_are_encrypted() -> None:
    encrypted = encrypt_credentials("top-secret", "X-Partner-Key")
    assert encrypted is not None
    assert "top-secret" not in encrypted
    assert decrypt_credentials(encrypted) == {
        "credential": "top-secret",
        "api_key_header": "X-Partner-Key",
    }
