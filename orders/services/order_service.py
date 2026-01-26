from decimal import Decimal

from django.db import transaction
from django.db.models import F

from pages.models import Product
from orders.models import Order, OrderItem, PaymentTransaction
from orders.services.inventory_service import lock_inventory
from orders.services.stripe import create_payment_intent


# =====================================================
# CREATE ORDER FROM CART (CANONICAL + SAFE)
# =====================================================
@transaction.atomic
def create_order_from_cart(*, user, cart, address_data, payment_method):
    """
    Creates an order and immutable order items.
    Inventory is NOT locked here unless COD.
    """

    subtotal = Decimal("0.00")
    order_items = []

    # Lock products to prevent oversell
    for product_id, item in cart.items():
        product = (
            Product.objects
            .select_for_update()
            .get(id=product_id, is_active=True)
        )

        qty = int(item.get("qty", 0))
        if qty <= 0 or qty > product.stock:
            raise ValueError("Invalid quantity")

        subtotal += product.price * qty
        order_items.append((product, qty))

    status = (
        Order.PAID if payment_method == "COD"
        else Order.PAYMENT_PENDING
    )

    order = Order.objects.create(
        user=user,
        full_name=address_data["full_name"],
        phone=address_data["phone"],
        address_line=address_data["address_line"],
        city=address_data["city"],
        state=address_data["state"],
        pincode=address_data["pincode"],
        country=address_data.get("country", "India"),
        subtotal=subtotal,
        total_amount=subtotal,
        currency="INR",
        status=status,
    )

    for product, qty in order_items:
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=getattr(product, "sku", ""),
            product_slug=product.slug,
            product_image=product.image.url if product.image else "",
            price=product.price,
            quantity=qty,
        )

    # Lock inventory immediately for COD orders
    if payment_method == "COD":
        lock_inventory(order)
        order.transition(Order.PROCESSING)

    return order


# =====================================================
# START STRIPE PAYMENT (IDEMPOTENT)
# =====================================================
@transaction.atomic
def start_online_payment(*, order):
    """
    Creates or reuses a Stripe PaymentIntent safely.
    """

    payment = (
        PaymentTransaction.objects
        .select_for_update()
        .filter(order=order, gateway="stripe")
        .first()
    )

    if payment and payment.client_secret:
        return payment

    intent = create_payment_intent(
        order=order,
        idempotency_key=f"order-{order.id}",
    )

    if payment is None:
        payment = PaymentTransaction.objects.create(
            order=order,
            gateway="stripe",
            intent_id=intent.id,
            client_secret=intent.client_secret,
            amount=order.total_amount,
            currency=order.currency,
            status=PaymentTransaction.CREATED,
            idempotency_key=f"order-{order.id}",
        )
    else:
        payment.intent_id = intent.id
        payment.client_secret = intent.client_secret
        payment.save(update_fields=["intent_id", "client_secret"])

    return payment


# =====================================================
# STRIPE PAYMENT SUCCESS (WEBHOOK ENTRY POINT)
# =====================================================
@transaction.atomic
def handle_successful_payment(*, payment_intent):
    """
    Finalizes payment and moves order forward exactly once.
    """

    order_id = payment_intent["metadata"].get("order_id")
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

    # Idempotent payment update
    if payment.status != PaymentTransaction.SUCCESS:
        payment.status = PaymentTransaction.SUCCESS
        payment.raw_response = payment_intent
        payment.save(update_fields=["status", "raw_response"])

    # Move order forward safely
    if order.status == Order.PAYMENT_PENDING:
        lock_inventory(order)
        order.transition(Order.PAID)
        order.transition(Order.PROCESSING)
