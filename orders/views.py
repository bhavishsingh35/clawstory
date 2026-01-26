from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from orders.services.inventory_service import restore_inventory

import stripe

from pages.models import Product
from orders.models import Order
from orders.services.order_service import (
    create_order_from_cart,
    start_online_payment,
)
from orders.services.stripe import (
    handle_payment_intent_succeeded,
    handle_payment_intent_failed,
)
from orders.services.webhook_service import (
    record_webhook_event,
    mark_webhook_processed,
)

stripe.api_key = settings.STRIPE_SECRET_KEY


# =====================================================
# CHECKOUT
# =====================================================
@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart:cart_detail")

    items = []
    subtotal = Decimal("0.00")

    for pid, item in cart.items():
        product = get_object_or_404(Product, id=pid, is_active=True)

        qty = int(item.get("qty", 0))
        if qty <= 0 or qty > product.stock:
            return redirect("cart:cart_detail")

        price = product.price
        line_total = price * qty
        subtotal += line_total

        items.append({
            "product": product,
            "quantity": qty,
            "price": price,
            "line_total": line_total,
        })

    return render(
        request,
        "orders/checkout.html",
        {
            "cart_items": items,
            "cart_subtotal": subtotal,
            "cart_total": subtotal,
        },
    )


# =====================================================
# CREATE ORDER
# =====================================================
@login_required
@require_POST
@transaction.atomic
def create_order(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart:cart_detail")

    payment_method = request.POST.get("payment_method")
    if payment_method not in ("COD", "ONLINE"):
        return redirect("orders:checkout")

    order = create_order_from_cart(
        user=request.user,
        cart=cart,
        address_data={
            "full_name": request.POST.get("full_name", "").strip(),
            "phone": request.POST.get("phone", "").strip(),
            "address_line": request.POST.get("address_line", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "state": request.POST.get("state", "").strip(),
            "pincode": request.POST.get("pincode", "").strip(),
            "country": "India",
        },
        payment_method=payment_method,
    )

    request.session["cart"] = {}
    request.session.modified = True

    if payment_method == "COD":
        return redirect("orders:order_success", order_id=order.id)

    start_online_payment(order=order)
    return redirect("orders:payment", order_id=order.id)


# =====================================================
# PAYMENT PAGE
# =====================================================
@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != Order.PAYMENT_PENDING:
        return redirect("orders:order_success", order_id=order.id)

    payment = (
        order.payments
        .filter(gateway="stripe")
        .only("client_secret")
        .first()
    )

    if not payment or not payment.client_secret:
        return redirect("orders:checkout")

    return render(
        request,
        "orders/payment.html",
        {
            "order": order,
            "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
            "client_secret": payment.client_secret,
        },
    )


# =====================================================
# ORDER SUCCESS / FAILURE
# =====================================================
@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_status.html", {"order": order})


@login_required
def payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/payment_failed.html", {"order": order})


# =====================================================
# ORDER CANCEL (USER-SAFE)
# =====================================================
@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status not in (
        Order.PAYMENT_PENDING,
        Order.PAID,
        Order.PROCESSING,
    ):
        messages.error(request, "Order cannot be cancelled at this stage.")
        return redirect("orders:order_detail", order_id=order.id)

    order.transition(Order.CANCEL_REQUESTED)
    messages.success(request, "Order cancellation requested.")

@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status not in (
        Order.PAYMENT_PENDING,
        Order.PAID,
        Order.PROCESSING,
    ):
        return redirect("orders:order_detail", order_id=order.id)

    order.transition(Order.CANCEL_REQUESTED)

    # 🔴 ADD THIS (THIS FIXES YOUR BUG)
    if order.stock_locked and not order.stock_restored:
        restore_inventory(order)

    return redirect("orders:order_detail", order_id=order.id)


# =====================================================
# STRIPE WEBHOOK (SOURCE OF TRUTH)
# =====================================================
@csrf_exempt
@transaction.atomic
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception:
        return HttpResponse(status=400)

    webhook = record_webhook_event(event=event)
    if webhook.processed:
        return HttpResponse(status=200)

    event_type = event["type"]
    intent = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        handle_payment_intent_succeeded(intent=intent)

    elif event_type in ("payment_intent.payment_failed", "payment_intent.canceled"):
        handle_payment_intent_failed(intent=intent)

    mark_webhook_processed(webhook=webhook)
    return HttpResponse(status=200)


# =====================================================
# USER ORDERS
# =====================================================
@login_required
def my_orders(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(request, "orders/my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        id=order_id,
        user=request.user,
    )
    return render(request, "orders/order_detail.html", {"order": order})
