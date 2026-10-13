"""Authentication routes: signup, login, token refresh, me."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app import catalyst_db
from app.catalyst_db import User
from app.schemas.auth import LoginIn, NameUpdateIn, PasswordChangeIn, SignupIn, TokenOut, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupIn):
    existing = await catalyst_db.get_user_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await catalyst_db.create_user(
        email=data.email, name=data.name, password_hash=hash_password(data.password), role="student"
    )
    return user


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn):
    user = await catalyst_db.get_user_by_email(data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(refresh_token: str):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await catalyst_db.get_user_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
async def update_me(data: NameUpdateIn, user: User = Depends(get_current_user)):
    updated = await catalyst_db.update_user(user.id, {"name": data.name.strip()})
    return updated


@router.post("/change-password")
async def change_password(
    data: PasswordChangeIn, user: User = Depends(get_current_user)
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await catalyst_db.update_user(user.id, {"password_hash": hash_password(data.new_password)})
    return {"ok": True}
