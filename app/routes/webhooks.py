import json
from fastapi import APIRouter, Request, HTTPException, Depends
import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.payment import Payment
from app.models.payment_link import PaymentLink
from app.core.logging import app_logger
from app.workers.tasks import process_stripe_payment

router = APIRouter(tags=["webhooks"])
@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)   # ya no es estrictamente necesaria, pero se puede dejar
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret
        )
    except Exception as e:
        app_logger.error(f"Webhook signature failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Solo nos interesa el evento de checkout completado
    if event["type"] == "checkout.session.completed":
        session_id = event["data"]["object"]["id"]
        # Encolar la tarea para procesar el pago de forma asíncrona
        process_stripe_payment.delay(session_id)
        app_logger.info(f"Task queued for session {session_id}")
        return {"status": "queued"}   # Respuesta rápida a Stripe

    return {"status": "success"}
