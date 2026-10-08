"""Auth request/response schemas."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Simple email validation: just requires @ and a dot in domain part.
# (Pydantic's EmailStr rejects .local domains like admin@certify.local)
EmailStrLocal = Annotated[str, StringConstraints(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$|^[^@\s]+@[^@\s]+$")]


class SignupIn(BaseModel):
    email: EmailStrLocal
    name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStrLocal
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class NameUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
