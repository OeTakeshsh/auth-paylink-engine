import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.payment_link import PaymentLink
from app.models.payment import Payment
from app.schemas.payment import PaymentResponse
from app.schemas.payment_link import PaymentLinkCreate, PaymentLinkResponse
from app.core.logging import app_logger
from uuid import uuid4
from app.core.config import settings


#routers
router = APIRouter(
    prefix="/payment-links",
    tags=["payment-links"],
    dependencies=[Depends(get_current_user)]   # Global dependency: all routes require auth
)

public_router = APIRouter(
        prefix="/payment-links",
        tags=["payment-links"]
)



@router.post("/", response_model=PaymentLinkResponse)
async def create_payment_link(
    data: PaymentLinkCreate,
    current_user: User = Depends(get_current_user),  # optional, already provided by router
    db: AsyncSession = Depends(get_db)
):
    app_logger.info(f"create payment link for user {current_user.id}")
    public_id = str(uuid4())[:8]
    payment_link = PaymentLink(
        user_id=current_user.id,
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        type=data.type,
        public_id=public_id,
        extra_data=data.extra_data or {}
    )
    db.add(payment_link)
    await db.commit()
    await db.refresh(payment_link)
    return payment_link

@router.get("/", response_model=list[PaymentLinkResponse])
async def list_payment_links(
    current_user: User = Depends(get_current_user),  # optional
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """List all payment links for the authenticated user (with pagination)."""
    result = await db.execute(
        select(PaymentLink)
        .where(PaymentLink.user_id == current_user.id)
        .order_by(PaymentLink.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    links = result.scalars().all()
    return links

# Public endpoint – overrides the global dependency
@public_router.get("/pay/{public_id}", dependencies=[])
async def get_payment_link_public(
    public_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Public endpoint to create a Stripe Checkout session and redirect to payment."""
    result = await db.execute(
        select(PaymentLink).where(PaymentLink.public_id == public_id, PaymentLink.status == "active")
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found")

    stripe.api_key = settings.stripe_secret_key

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": link.currency.lower(),
                    "product_data": {"name": link.title},
                    "unit_amount": int(link.amount * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url = "http://localhost:8000/payment-links/payment-success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url = "http://localhost:8000/payment-links/payment-cancel",
            metadata={
                "payment_link_id": str(link.id),
                "public_id": public_id,
            }
        )
        return {"checkout_url": session.url}
    except Exception as e:
        app_logger.error(f"Stripe checkout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating payment session")

@router.get("/payments", response_model=list[PaymentResponse])
async def list_user_payments(
    current_user: User = Depends(get_current_user),  # optional
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """List all payments made by the authenticated user (with pagination)."""
    result = await db.execute(
        select(Payment)
        .join(PaymentLink, Payment.payment_link_id == PaymentLink.id)
        .where(PaymentLink.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    payments = result.scalars().all()
    return payments

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_detail(
    payment_id: int,
    current_user: User = Depends(get_current_user),  # optional
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific payment (only if it belongs to the user)."""
    result = await db.execute(
        select(Payment)
        .join(PaymentLink, Payment.payment_link_id == PaymentLink.id)
        .where(
            Payment.id == payment_id,
            PaymentLink.user_id == current_user.id
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

# Endpoints de redirección para Stripe (públicos, no requieren autenticación)
@public_router.get("/payment-success", dependencies=[])
async def payment_success(session_id: str = None):
    """Stripe redirige aquí tras un pago exitoso."""
    return {"message": "Payment successful", "session_id": session_id}

@public_router.get("/payment-cancel", dependencies=[])
async def payment_cancel():
    """Stripe redirige aquí si el usuario cancela el pago."""
    return {"message": "Payment cancelled"}
