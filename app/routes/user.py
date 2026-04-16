from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import app_logger

from app.core.auth import (
    create_user_access_token,
    create_user_refresh_token,
    revoke_refresh_token,
    store_refresh_token,
    verify_refresh_token,
    decode_refresh_token,
)

from app.core.security import hash_password, verify_password

from app.models.user import User
from app.schemas.user import(
    LoginRequest,
    LogoutRequest,
    UserCreate,
    UserResponse,
    RefreshRequest
)

from app.core.dependencies import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/login")
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    app_logger.info(f"login attempt: {login_data.username}")

    result = await db.execute(select(User).where(User.email == login_data.username))
    db_user = result.scalar_one_or_none()
    if not db_user or not verify_password(login_data.password, db_user.password):
        app_logger.warning(f"login failed: {login_data.username} - invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciales incorrectas"
        )

    access_token = create_user_access_token(db_user)
    refresh_token = create_user_refresh_token(db_user)
    payload = decode_refresh_token(refresh_token)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    await store_refresh_token(db, db_user.id, refresh_token, expires_at)

    app_logger.info(f"login success: {db_user.email} (user_id: {db_user.id})")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    data: LogoutRequest,
    db: AsyncSession = Depends(get_db)
):
    token = data.refresh_token
    app_logger.info("logout attempt")

    try:
        payload = decode_refresh_token(token)
    except HTTPException as e:
        app_logger.warning(f"logout failed: invalid token format - {e.detail}")
        raise

    user_id = payload.get("user_id")
    if user_id is None:
        app_logger.warning("logout failed: user_id not found in token")
        raise HTTPException(401, "token invalido: user_id no encontrado")

    is_valid = await verify_refresh_token(db, user_id, token)
    if not is_valid:
        app_logger.warning(f"logout attempt with invalid/revoked token for user_id {user_id}")

    await revoke_refresh_token(db, user_id, token)
    app_logger.info(f"logout success for user_id: {user_id}")
    return {"message": "logout exitoso"}


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    app_logger.info(f"create user attempt: {user.email}")

    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        app_logger.warning(f"create user failed: {user.email} - email already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="el correo electronico ya se encuentra registrado"
        )

    new_user = User(
        email=user.email,
        password=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    app_logger.info(f"create user success: {new_user.email} (user_id: {new_user.id})")
    return new_user


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    app_logger.info(f"get me: user_id {current_user.id}")
    return {
        "id": current_user.id,
        "email": current_user.email
    }


@router.post("/refresh")
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    token = data.refresh_token
    app_logger.info("refresh token attempt")

    try:
        payload = decode_refresh_token(token)
    except HTTPException as e:
        app_logger.warning(f"refresh token decode failed: {e.detail}")
        raise

    user_id = payload["user_id"]
    if not await verify_refresh_token(db, user_id, token):
        app_logger.warning(f"refresh token failed for user_id {user_id}: invalid or revoked")
        raise HTTPException(401, "token de refresco invalido o revocado")

    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        app_logger.warning(f"refresh token failed: user {user_id} not found")
        raise HTTPException(401, "usuario no identificado")

    new_access_token = create_user_access_token(db_user)
    app_logger.info(f"refresh token success for user_id {user_id}")

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

