from pydantic import BaseModel
from datetime import datetime
from typing import Optional

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

    model_config = {"from_attributes": True}
