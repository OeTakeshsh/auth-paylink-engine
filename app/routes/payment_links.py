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

router = APIRouter(prefix="/payment-links", tags=["payment-links"])

@router.post("/", response_model=PaymentLinkResponse)
async def create_payment_link(
    data: PaymentLinkCreate,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,          # ← nuevo parámetro
    limit: int = 20         # ← nuevo parámetro
):
    """Lista todos los payment links del usuario autenticado (con paginación)."""
    result = await db.execute(
        select(PaymentLink)
        .where(PaymentLink.user_id == current_user.id)
        .order_by(PaymentLink.created_at.desc())
        .offset(skip)       # ← añadido
        .limit(limit)       # ← añadido
    )
    links = result.scalars().all()
    return links

@router.get("/pay/{public_id}")
async def get_payment_link_public(
    public_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Endpoint público para crear una sesión de Stripe Checkout y redirigir al pago."""
    # Buscar el payment link por public_id
    result = await db.execute(
        select(PaymentLink).where(PaymentLink.public_id == public_id, PaymentLink.status == "active")
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found")

    # Configurar Stripe con la clave secreta
    stripe.api_key = settings.stripe_secret_key

    # Crear sesión de Checkout
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": link.currency.lower(),
                    "product_data": {"name": link.title},
                    "unit_amount": int(link.amount * 100),  # Stripe usa centavos
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://tu-sitio.com/success",   # Cambia por tu URL real
            cancel_url="https://tu-sitio.com/cancel",
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,          # ← nuevo parámetro
    limit: int = 20         # ← nuevo parámetro
):
    """Lista todos los pagos realizados por el usuario autenticado (con paginación)."""
    result = await db.execute(
        select(Payment)
        .join(PaymentLink, Payment.payment_link_id == PaymentLink.id)
        .where(PaymentLink.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .offset(skip)       # ← añadido
        .limit(limit)       # ← añadido
    )
    payments = result.scalars().all()
    return payments

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_detail(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de un pago específico (solo si pertenece al usuario)."""
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

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_detail(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de un pago específico (solo si pertenece al usuario)."""
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
