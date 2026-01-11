from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from pages.models import Product


# =========================
# CART DETAIL
# =========================
@login_required
def cart_detail(request):
    cart = request.session.get("cart", {})
    products = Product.objects.filter(id__in=cart.keys())

    cart_items = []
    total = 0

    for product in products:
        qty = cart.get(str(product.id), 0)
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


# =========================
# ADD TO CART
# =========================
@login_required
def cart_add(request, product_id):
    cart = request.session.get("cart", {})
    product_id = str(product_id)

    qty = int(request.POST.get("quantity", 1))

    if product_id in cart:
        cart[product_id] += qty
    else:
        cart[product_id] = qty

    request.session["cart"] = cart
    return redirect("cart:cart_detail")


# =========================
# REMOVE ITEM
# =========================
@login_required
def cart_remove(request, product_id):
    cart = request.session.get("cart", {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session["cart"] = cart
    return redirect("cart:cart_detail")


# =========================
# UPDATE CART (+ / −)
# =========================
@login_required
def cart_update(request, product_id):
    cart = request.session.get("cart", {})
    product_id = str(product_id)

    product = get_object_or_404(Product, id=product_id)
    current_qty = cart.get(product_id, 0)

    action = request.POST.get("action")

    if action == "inc":
        if current_qty < product.stock:   # 🔥 STOCK CHECK
            cart[product_id] = current_qty + 1

    elif action == "dec":
        if current_qty > 1:
            cart[product_id] = current_qty - 1
        else:
            cart.pop(product_id, None)

    request.session["cart"] = cart
    return redirect("cart:cart_detail")