from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "UniBiz"
    app_env: Literal["development", "production", "test"] = "development"
    app_secret_key: str = Field(min_length=32)
    bootstrap_token: str = Field(min_length=16)
    database_url: str
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:8001"]
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    webhook_encryption_key: str
    login_max_failures: int = Field(default=5, ge=3, le=20)
    login_lock_minutes: int = Field(default=15, ge=1, le=1440)
    max_request_body_bytes: int = Field(default=2_097_152, ge=65_536, le=20_971_520)
    trusted_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1"]

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env != "production":
            return self
        unsafe_markers = ("replace", "change-me", "local", "test", "password")
        secrets = (self.app_secret_key, self.bootstrap_token, self.webhook_encryption_key)
        if any(marker in value.lower() for value in secrets for marker in unsafe_markers):
            raise ValueError(
                "Production secrets must be random and must not use placeholder values"
            )
        if any(not origin.startswith("https://") for origin in self.cors_origins):
            raise ValueError("Production CORS origins must use HTTPS")
        if "*" in self.trusted_hosts:
            raise ValueError("Production trusted hosts must not contain a wildcard")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
