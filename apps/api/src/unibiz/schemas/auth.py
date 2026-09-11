from pydantic import BaseModel, Field


class BootstrapStatus(BaseModel):
    initialized: bool


class BootstrapAdminRequest(BaseModel):
    bootstrap_token: str
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    permissions: list[str]
    is_superuser: bool
