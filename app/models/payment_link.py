from sqlalchemy import String, Numeric, JSON, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from uuid import uuid4
from datetime import datetime
from typing import Optional

class PaymentLink(Base):
    __tablename__ = "payment_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Optional[float]] = mapped_column(Numeric(10,2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CLP")
    type: Mapped[str] = mapped_column(String(20), default="fixed")
    status: Mapped[str] = mapped_column(String(20), default="active")
    public_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, default=lambda: str(uuid4())[:8])
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
