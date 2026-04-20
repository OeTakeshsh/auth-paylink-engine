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

router = APIRouter(tags=["webhooks"])

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
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

    if event["type"] == "checkout.session.completed":
        # Convertir StripeObject a dict para usar .get()
        session_obj = event["data"]["object"]
        session_dict = session_obj.to_dict() if hasattr(session_obj, "to_dict") else dict(session_obj)

        metadata = session_dict.get("metadata", {})
        app_logger.info(f"session metadata: {metadata}")

        payment_link_id = metadata.get("payment_link_id")
        if not payment_link_id:
            app_logger.warning("Missing payment_link_id in metadata")
            return {"ok": True}

        result = await db.execute(
            select(PaymentLink).where(PaymentLink.id == int(payment_link_id))
        )
        link = result.scalar_one_or_none()

        if not link:
            app_logger.warning(f"PaymentLink not found: {payment_link_id}")
            return {"ok": True}

        # Idempotencia
        existing = await db.execute(
            select(Payment).where(Payment.provider_payment_id == session_dict["id"])
        )
        if existing.scalar_one_or_none():
            app_logger.info("Payment already processed")
            return {"ok": True}

        # Crear pago
        payment = Payment(
            payment_link_id=link.id,
            provider="stripe",
            provider_payment_id=session_dict["id"],
            amount=session_dict["amount_total"] / 100,
            currency=session_dict["currency"],
            status="succeeded",
            extra_data=session_dict   # guarda el dict
        )

        db.add(payment)
        await db.commit()

        app_logger.info(f"Payment stored: {payment.id}")
        app_logger.info(f"event type: {event['type']}")
        # Elimina o corrige la línea que causa el error:
        # app_logger.info(f"full event: {json.dumps(event, indent=2)}")
        # Si quieres loguear el evento, conviértelo a dict:
        # app_logger.info(f"full event: {json.dumps(event.to_dict(), indent=2)}")

    return {"status": "success"}
