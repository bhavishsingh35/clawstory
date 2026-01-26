import logging
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings

from orders.models import Order, PaymentTransaction
from orders.services.inventory_service import lock_inventory, restore_inventory

logger = logging.getLogger("payments.stripe")

stripe.api_key = settings.STRIPE_SECRET_KEY


# ======================================================
# INTERNAL HELPERS
# ======================================================
def _to_cents(amount: Decimal) -> int:
    if amount is None or amount <= 0:
        raise ValueError("Amount must be greater than zero")

    return int(
        amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100
    )


# ======================================================
# CREATE PAYMENT INTENT (STRIPE ONLY)
# ======================================================
def create_payment_intent(*, order: Order, idempotency_key: str):
    """
    Stripe-only responsibility.
    No database writes.
    """

    intent = stripe.PaymentIntent.create(
        amount=_to_cents(order.total_amount),
        currency=order.currency.lower(),
        metadata={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "user_id": str(order.user_id),
        },
        automatic_payment_methods={"enabled": True},
        idempotency_key=idempotency_key,
    )

    logger.info(
        "Stripe PaymentIntent created",
        extra={
            "order_id": str(order.id),
            "intent_id": intent.id,
        },
    )

    return intent


# ======================================================
# RETRIEVE EXISTING INTENT
# ======================================================
def retrieve_payment_intent(intent_id):
    return stripe.PaymentIntent.retrieve(intent_id)


# ======================================================
# WEBHOOK EVENT HANDLERS (IDEMPOTENT)
# ======================================================
def handle_payment_intent_succeeded(*, intent):
    """
    Finalize successful payment exactly once.
    """

    order_id = intent.metadata.get("order_id")
    if not order_id:
        return

    order = (
        Order.objects
        .select_for_update()
        .filter(id=order_id)
        .first()
    )
    if not order:
        return

    payment = (
        PaymentTransaction.objects
        .select_for_update()
        .filter(order=order, gateway="stripe")
        .first()
    )
    if not payment:
        return

    if payment.status != PaymentTransaction.SUCCESS:
        payment.status = PaymentTransaction.SUCCESS
        payment.raw_response = intent
        payment.charge_id = intent.latest_charge
        payment.save(update_fields=["status", "raw_response", "charge_id"])

    if order.status == Order.PAYMENT_PENDING:
        lock_inventory(order)
        order.transition(Order.PAID)
        order.transition(Order.PROCESSING)


def handle_payment_intent_failed(*, intent):
    """
    Handle failed or canceled payments safely.
    """

    order_id = intent.metadata.get("order_id")
    if not order_id:
        return

    order = (
        Order.objects
        .select_for_update()
        .filter(id=order_id)
        .first()
    )
    if not order:
        return

    if order.status in (Order.PAID, Order.CANCELLED, Order.REFUNDED):
        return
    
    if order.stock_locked and not order.stock_restored:
        restore_inventory(order)

    order.transition(Order.PAYMENT_FAILED)
    restore_inventory(order)


# ======================================================
# VERIFY STRIPE WEBHOOK
# ======================================================
def verify_webhook(*, payload: bytes, signature: str):
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
