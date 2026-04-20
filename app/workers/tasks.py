from app.workers.celery_app import celery_app
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.payment import Payment
from app.models.payment_link import PaymentLink
from app.core.logging import app_logger
import stripe
@celery_app.task

def send_test_email(email:str):
    print(f"Sending email to {email}")
    return f"Email sent to {email}"

 Motor síncrono para Celery (no usa asyncpg)
SYNC_DATABASE_URL = settings.database_url.replace('+asyncpg', '')
engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)




@shared_task
def process_stripe_payment(session_id: str):
    db = SessionLocal()
    try:
        stripe.api_key = settings.stripe_secret_key
        session = stripe.checkout.Session.retrieve(session_id)
        metadata = session.get('metadata', {})
        payment_link_id = metadata.get('payment_link_id')
        if not payment_link_id:
            app_logger.warning("Missing payment_link_id")
            return

        # Idempotencia
        existing = db.query(Payment).filter(Payment.provider_payment_id == session_id).first()
        if existing:
            app_logger.info(f"Payment {session_id} already processed")
            return

        link = db.query(PaymentLink).filter(PaymentLink.id == int(payment_link_id)).first()
        if not link:
            app_logger.warning(f"PaymentLink {payment_link_id} not found")
            return

        payment = Payment(
            payment_link_id=link.id,
            provider="stripe",
            provider_payment_id=session_id,
            amount=session["amount_total"] / 100,
            currency=session["currency"],
            status="succeeded",
            extra_data=dict(session)
        )
        db.add(payment)
        db.commit()
        app_logger.info(f"Payment stored: {payment.id}")
    except Exception as e:
        app_logger.error(f"Celery task error: {str(e)}")
        db.rollback()
    finally:
        db.close()
