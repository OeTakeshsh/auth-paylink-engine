from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class PaymentLinkCreate(BaseModel):
    title: str
    amount: Optional[float] = None
    currency: str = "CLP"
    type: str = "fixed"
    extra_data: Optional[Dict] = {}
class PaymentLinkResponse(BaseModel):
    id: int
    title: str
    amount: Optional[float]
    currency: str
    type: str
    status: str
    public_id: str
    created_at: datetime
    extra_data: Optional[Dict] = None
    model_config = {"from_attributes": True}
class PaymentResponse(BaseModel):
    id: int
    payment_link_id: int
    provider: str
    provider_payment_id: str
    amount: float
    currency: str
    status: str
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config={"from_attributes": True}
