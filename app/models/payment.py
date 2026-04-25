from sqlalchemy import String, Numeric, JSON, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from datetime import datetime
from typing import Optional
from sqlalchemy import UniqueConstraint

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_link_id: Mapped[int] = mapped_column(ForeignKey("payment_links.id"))
    
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=True)
    provider: Mapped[str] = mapped_column(String(20))  # stripe, mercadopago
    
    provider_payment_id: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Numeric(10,2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)  
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("provider_payment_id", name="uq_provider_payment_id"),
    )
