from app.workers.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError               
from app.core.config import settings
from app.models.payment import Payment
from app.models.payment_link import PaymentLink
from app.core.logging import app_logger
import stripe

# Synchronous engine for Celery (no asyncpg)
SYNC_DATABASE_URL = settings.database_url.replace("+asyncpg", "")
engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery_app.task
def process_stripe_payment(session_id: str):
    db = SessionLocal()
    try:
        stripe.api_key = settings.stripe_secret_key

        # Retrieve Stripe session
        session = stripe.checkout.Session.retrieve(session_id)
        session_dict = session.to_dict()

        # Safe metadata extraction
        metadata = session_dict.get("metadata", {})
        payment_link_id = metadata.get("payment_link_id")

        if not payment_link_id:
            app_logger.warning("Missing payment_link_id in session metadata")
            return

        # Look up the payment link
        link = (
            db.query(PaymentLink)
            .filter(PaymentLink.id == int(payment_link_id))
            .first()
        )
        if not link:
            app_logger.warning(f"PaymentLink {payment_link_id} not found")
            return

        # Create payment (let the UNIQUE constraint handle duplicates)
        payment = Payment(
            payment_link_id=link.id,
            provider="stripe",
            provider_payment_id=session_id,
            amount=session_dict["amount_total"] / 100,
            currency=session_dict["currency"],
            status="succeeded",
            extra_data=session_dict,
        )

        db.add(payment)
        db.commit()

        app_logger.info(f"Payment stored: {payment.id}")

    except IntegrityError:
        db.rollback()
        app_logger.info(f"Payment {session_id} already processed (idempotent)")
    except Exception as e:
        app_logger.error(f"Celery task error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
