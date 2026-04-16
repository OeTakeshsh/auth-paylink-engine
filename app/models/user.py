from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from datetime import datetime, timezone
from typing import Optional



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)


class UserToken(Base):
    """
    Representa la tabla 'user_tokens' encargada de almacenar los hashes
    de los refresh tokens activos para cada usuario.
    """
    __tablename__ = "user_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        #index=True "aparentemente redundante
    )
    
    token_hash: Mapped[str] = mapped_column(String(64), index=True)

    created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),  # <-- TIMESTAMP WITH TIME ZONE
    server_default=func.now()  # <-- usa hora del servidor PostgreSQL
    )

    revoked: Mapped[bool] = mapped_column(Boolean,default=False,nullable=False)  
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=True)

    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
            DateTime(timezone=True),
            nullable=True)

