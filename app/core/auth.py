import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_db
from app.models.user import User, UserToken 
from app.core.config import settings

# ==================== HELPERS ====================
def _base_user_payload(user: User) -> dict:  
    return {"sub": user.email, "user_id": user.id}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ==================== CREACIÓN DE TOKENS ====================
"""
REFACTORIZAR!!!
"""

def create_access_token(data: dict) -> str:
    if "sub" not in data or "user_id" not in data:
        raise ValueError("El payload requiere 'sub' y 'user_id'.")
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access"
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_refresh_token(data: dict) -> str:
    if "sub" not in data or "user_id" not in data:
        raise ValueError("El payload requiere 'sub' y 'user_id'.")
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh"
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_user_access_token(user: User) -> str:
    return create_access_token(_base_user_payload(user))


def create_user_refresh_token(user: User) -> str:
    return create_refresh_token(_base_user_payload(user))

# ==================== REVOCACION DE TOKENS =================

async def revoke_refresh_token(db: AsyncSession, user_id: int, token: str) -> None:
    token_hash = hash_token(token)
    await db.execute(
            update(UserToken)
            .where(
                UserToken.user_id == user_id,
                UserToken.token_hash == token_hash
                )
            .values(revoked = True)
            )
    await db.commit()

# ==================== OPERACIONES EN DB ====================
async def store_refresh_token(
    db: AsyncSession,
    user_id: int,
    token: str,
    expires_at: datetime,
    device_name: Optional[str] = None,    
    ip_address: Optional[str] = None      
) -> None:
    refresh_hash = hash_token(token)
    new_token = UserToken(
        user_id=user_id,
        token_hash=refresh_hash,
        expires_at=expires_at,
        revoked=False,
        device_name=device_name,
        ip_address=ip_address,
        last_used_at=datetime.now(timezone.utc)
    )
    db.add(new_token)
    await db.commit()

async def verify_refresh_token(db: AsyncSession, user_id: int, token: str) -> bool:
    """Verifica que el hash del refresh token exista en la DB y NO esté revocado"""
    token_hash = hash_token(token)
    result = await db.execute(
        select(UserToken).where(
            UserToken.user_id == user_id,
            UserToken.token_hash == token_hash,
            UserToken.revoked == False
        )
    )
    return result.scalar_one_or_none() is not None
# ==================== DECODIFICACIÓN ====================
def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Tipo de token inválido: se esperaba {expected_type}"
            )

        if "user_id" not in payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El payload del token está incompleto"
            )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"El token de {expected_type} ha expirado"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar la firma del token"
        )


def decode_access_token(token: str) -> dict:
    return decode_token(token, "access")


def decode_refresh_token(token: str) -> dict:
    return decode_token(token, "refresh")


# ==================== DEPENDENCIAS DE AUTENTICACIÓN ====================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Obtiene el usuario autenticado según el access token que llegue.
    """
    # 1. Decodificar access token
    payload = decode_access_token(token)

    # 2. Extraer user_id
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: user_id no encontrado"
        )

    # 3. Buscar usuario en BD
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )

    return user 
