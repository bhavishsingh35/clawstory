from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from .models import Order, OrderItem
from pages.models import Product


@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart:cart_detail")  # your existing cart page
    return render(request, "orders/checkout.html")


@login_required
def create_order(request):
    if request.method != "POST":
        return redirect("orders:checkout")

    payment_method = request.POST.get("payment_method")
    cart = request.session.get("cart", {})

    if not payment_method or not cart:
        return redirect("orders:checkout")

    # calculate total
    total = 0
    for product_id, qty in cart.items():
        product = Product.objects.get(id=product_id)
        total += product.price * qty

    # create order
    order = Order.objects.create(
        user=request.user,
        total=total,
        payment_method=payment_method,
        payment_status="PENDING",
        status="PLACED"
    )

    # create order items
    for product_id, qty in cart.items():
        product = Product.objects.get(id=product_id)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=product.price
        )

    # COD → instant success
    if payment_method == "COD":
        order.payment_status = "SUCCESS"
        order.status = "CONFIRMED"
        order.save()
        request.session["cart"] = {}
        return redirect("orders:order_success", order_id=order.id)

    # ONLINE PAYMENT → start 10 min timer
    order.payment_expires_at = timezone.now() + timedelta(minutes=10)
    order.save()

    return redirect("orders:payment", order_id=order.id)


@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_status != "PENDING":
        return redirect("orders:order_success", order_id=order.id)

    if timezone.now() > order.payment_expires_at:
        order.payment_status = "FAILED"
        order.save()
        return redirect("orders:payment_failed", order_id=order.id)

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

    if timezone.now() > order.payment_expires_at:
        order.payment_status = "FAILED"
        order.save()
        return redirect("orders:payment_failed", order_id=order.id)

    order.payment_status = "SUCCESS"
    order.status = "CONFIRMED"
    order.save()

    request.session["cart"] = {}
    return redirect("orders:order_success", order_id=order.id)


@login_required
def payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/payment_failed.html", {"order": order})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_success.html", {"order": order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/my_orders.html", {"orders": orders})