from pydantic import BaseModel, Field


class AuthStatus(BaseModel):
    configured: bool
    authenticated: bool
    setup_code_required: bool


class Passphrase(BaseModel):
    passphrase: str = Field(min_length=1, max_length=200)


class Setup(Passphrase):
    setup_code: str = Field(default="", max_length=200)


class NewPassphrase(BaseModel):
    current: str = Field(min_length=1, max_length=200)
    new: str = Field(min_length=1, max_length=200)
