from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from pages.models import Product

@login_required
def cart_detail(request):
    cart = request.session.get("cart", {})
    products = Product.objects.filter(id__in=cart.keys())

    cart_items = []
    total = 0

    for product in products:
        qty = cart[str(product.id)]
        subtotal = product.price * qty
        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": qty,
            "subtotal": subtotal,
        })

    return render(request, "cart/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })

@login_required
def cart_add(request, product_id):
    cart = request.session.get("cart", {})
    product_id = str(product_id)

    qty = int(request.GET.get("qty", 1))  # DEFAULT = 1

    if product_id in cart:
        cart[product_id] += qty
    else:
        cart[product_id] = qty

    request.session["cart"] = cart
    return redirect("cart:cart_detail")

@login_required
def cart_remove(request, product_id):
    cart = request.session.get("cart", {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session["cart"] = cart
    return redirect("cart:cart_detail")

def cart_update(request, product_id):
    cart = request.session.get("cart", {})
    product_id = str(product_id)

    qty = int(request.POST.get("qty", 1))

    if qty <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = qty

    request.session["cart"] = cart
    return redirect("cart:cart_detail")