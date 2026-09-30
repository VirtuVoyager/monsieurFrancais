from pydantic import BaseModel, Field


class AuthStatus(BaseModel):
    configured: bool
    authenticated: bool


class Passphrase(BaseModel):
    passphrase: str = Field(min_length=1, max_length=200)
