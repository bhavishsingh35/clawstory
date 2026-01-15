from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from decimal import Decimal
from datetime import timedelta
import json
import re

from .models import Order, OrderItem, PaymentTransaction, RazorpayWebhookEvent
from pages.models import Product
from orders.services.razorpay import (
    create_order as create_razorpay_order,
    verify_signature,
    verify_webhook_signature,
)


# ======================================================
# CHECKOUT
# ======================================================
@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart:cart_detail")

    items = []
    subtotal = Decimal("0.00")

    for product_id, qty in cart.items():
        product = get_object_or_404(Product, id=product_id)

        if qty > product.stock:
            return redirect("cart:cart_detail")

        line_total = product.price * qty
        subtotal += line_total

        items.append(
            {
                "product": product,
                "quantity": qty,
                "line_total": line_total,
            }
        )

    return render(
        request,
        "orders/checkout.html",
        {
            "cart_items": items,
            "cart_subtotal": subtotal,
            "cart_total": subtotal,
        },
    )


# ======================================================
# CREATE ORDER
# ======================================================
@login_required
@transaction.atomic
def create_order(request):
    if request.method != "POST":
        return redirect("orders:checkout")

    cart = request.session.get("cart", {})
    payment_method = request.POST.get("payment_method")

    if not cart or payment_method not in (
        Order.PAYMENT_COD,
        Order.PAYMENT_ONLINE,
    ):
        return redirect("orders:checkout")

    full_name = request.POST.get("full_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    address_line = request.POST.get("address_line", "").strip()
    city = request.POST.get("city", "").strip()
    state = request.POST.get("state", "").strip()
    pincode = request.POST.get("pincode", "").strip()

    if not all([full_name, phone, address_line, city, state, pincode]):
        return redirect("orders:checkout")

    if not re.fullmatch(r"\d{10}", phone):
        return redirect("orders:checkout")

    if not re.fullmatch(r"\d{6}", pincode):
        return redirect("orders:checkout")

    subtotal = Decimal("0.00")
    locked_products = {}

    for pid, qty in cart.items():
        product = Product.objects.select_for_update().get(id=pid)
        if qty > product.stock:
            return redirect("cart:cart_detail")

        locked_products[pid] = product
        subtotal += product.price * qty

    shipping_charge = Decimal("0.00")
    tax = Decimal("0.00")
    total_amount = subtotal + shipping_charge + tax

    order = Order.objects.create(
        user=request.user,
        full_name=full_name,
        phone=phone,
        address_line=address_line,
        city=city,
        state=state,
        pincode=pincode,
        subtotal=subtotal,
        shipping_charge=shipping_charge,
        tax=tax,
        total_amount=total_amount,
        payment_method=payment_method,
        payment_expires_at=timezone.now() + timedelta(minutes=15),
    )

    for pid, qty in cart.items():
        product = locked_products[pid]
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            price=product.price,
            quantity=qty,
        )

    if payment_method == Order.PAYMENT_COD:
        for item in order.items.select_related("product"):
            item.product.stock -= item.quantity
            item.product.save(update_fields=["stock"])

        order.status = Order.STATUS_PROCESSING
        order.payment_status = Order.PAYMENT_SUCCESS
        order.save(update_fields=["status", "payment_status"])

        request.session["cart"] = {}
        return redirect("orders:order_success", order.id)

    return redirect("orders:payment", order.id)


# ======================================================
# PAYMENT PAGE
# ======================================================
@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_status == Order.PAYMENT_SUCCESS:
        return redirect("orders:order_success", order.id)

    if order.payment_expires_at and timezone.now() > order.payment_expires_at:
        order.mark_failed()
        return redirect("orders:payment_failed", order.id)

    if not order.razorpay_order_id:
        rz_order = create_razorpay_order(
            amount=order.total_amount,
            currency=order.currency,
            receipt=str(order.id),
        )

        order.mark_payment_pending(rz_order["id"])

        PaymentTransaction.objects.create(
            order=order,
            gateway="razorpay",
            gateway_order_id=rz_order["id"],   # ✅ correct field
            amount=order.total_amount,
            currency=order.currency,
            status=PaymentTransaction.STATUS_CREATED,
            raw_response=rz_order,
        )

    remaining_seconds = int(
        (order.payment_expires_at - timezone.now()).total_seconds()
    )

    return render(
        request,
        "orders/payment.html",
        {
            "order": order,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_amount": int(order.total_amount * 100),
            "remaining_seconds": remaining_seconds,
        },
    )


# ======================================================
# PAYMENT FAILED
# ======================================================
@login_required
def payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/payment_failed.html", {"order": order})


# ======================================================
# ORDER SUCCESS
# ======================================================
@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_success.html", {"order": order})


# ======================================================
# RAZORPAY WEBHOOK (SOURCE OF TRUTH)
# ======================================================
@csrf_exempt
@transaction.atomic
def razorpay_webhook(request):
    body = request.body
    signature = request.headers.get("X-Razorpay-Signature")

    try:
        verify_webhook_signature(body, signature)
    except Exception:
        return HttpResponse(status=400)

    payload = json.loads(body.decode("utf-8"))
    event_id = payload.get("id")

    if RazorpayWebhookEvent.objects.filter(event_id=event_id).exists():
        return HttpResponse(status=200)

    RazorpayWebhookEvent.objects.create(
        event_id=event_id,
        event_type=payload.get("event"),
        payload=payload,
        processed=True,
    )

    if payload.get("event") == "payment.captured":
        entity = payload["payload"]["payment"]["entity"]
        razorpay_order_id = entity.get("order_id")
        razorpay_payment_id = entity.get("id")

        order = Order.objects.select_for_update().get(
            razorpay_order_id=razorpay_order_id
        )

        if order.payment_status != Order.PAYMENT_SUCCESS:
            for item in order.items.select_related("product"):
                item.product.stock -= item.quantity
                item.product.save(update_fields=["stock"])

            order.mark_paid(
                payment_id=razorpay_payment_id,
                signature="webhook",
            )

            PaymentTransaction.objects.filter(
                razorpay_order_id=razorpay_order_id
            ).update(
                razorpay_payment_id=razorpay_payment_id,
                status=PaymentTransaction.STATUS_SUCCESS,
                raw_response=entity,
            )

    return HttpResponse(status=200)


# ======================================================
# MY ORDERS
# ======================================================
@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
