from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from .models import Order, OrderItem
from pages.models import Product


ORDER_STEPS = [
    "PLACED",
    "CONFIRMED",
    "PACKED",
    "DISPATCHED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
]


@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart:cart_detail")

    items = []
    total = 0

    for product_id, qty in cart.items():
        product = get_object_or_404(Product, id=product_id)
        line_total = product.price * qty
        total += line_total

        items.append({
            "product": product,
            "quantity": qty,
            "line_total": line_total,
        })

    return render(request, "orders/checkout.html", {
        "cart_items": items,
        "cart_total": total,
    })


@login_required
def create_order(request):
    if request.method != "POST":
        return redirect("orders:checkout")

    payment_method = request.POST.get("payment_method")
    cart = request.session.get("cart", {})

    if not payment_method or not cart:
        return redirect("orders:checkout")

    total = 0
    products_cache = {}

    for product_id, qty in cart.items():
        product = get_object_or_404(Product, id=product_id)
        products_cache[product_id] = product
        total += product.price * qty

    order = Order.objects.create(
        user=request.user,
        total=total,
        payment_method=payment_method,
        payment_status="PENDING",
        status="PLACED",
        payment_expires_at=timezone.now() + timedelta(minutes=10)
    )

    for product_id, qty in cart.items():
        product = products_cache[product_id]
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=product.price
        )

    if payment_method == "COD":
        order.payment_status = "SUCCESS"
        order.status = "CONFIRMED"
        order.save()
        request.session["cart"] = {}
        return redirect("orders:order_success", order.id)

    return redirect("orders:payment", order.id)


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")

    orders_data = []
    for order in orders:
        current_step = (
            ORDER_STEPS.index(order.status)
            if order.status in ORDER_STEPS else -1
        )
        orders_data.append({
            "order": order,
            "current_step": current_step,
        })

    return render(request, "orders/my_orders.html", {
        "orders_data": orders_data,
        "ORDER_STEPS": ORDER_STEPS,
    })


@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_status != "PENDING":
        return redirect("orders:order_success", order.id)

    if order.is_payment_expired():
        order.payment_status = "FAILED"
        order.save()
        return redirect("orders:payment_failed", order.id)

    remaining_seconds = int(
        (order.payment_expires_at - timezone.now()).total_seconds()
    )

    return render(request, "orders/payment.html", {
        "order": order,
        "remaining_seconds": remaining_seconds,
    })


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_payment_expired():
        order.payment_status = "FAILED"
        order.save()
        return redirect("orders:payment_failed", order.id)

    order.payment_status = "SUCCESS"
    order.status = "CONFIRMED"
    order.save()

    request.session["cart"] = {}
    return redirect("orders:order_success", order.id)


@login_required
def payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/payment_failed.html", {"order": order})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_success.html", {"order": order})