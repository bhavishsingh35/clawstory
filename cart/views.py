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
    updated = False  # track auto-fixes

    for product in products:
        pid = str(product.id)
        qty = cart.get(pid, 0)

        # 🔒 HARD STOCK VALIDATION
        if product.stock == 0:
            cart.pop(pid)
            updated = True
            continue

        if qty > product.stock:
            qty = product.stock
            cart[pid] = qty
            updated = True

        subtotal = product.price * qty
        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": qty,
            "subtotal": subtotal,
        })

    if updated:
        request.session["cart"] = cart

    return render(request, "cart/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })


# =========================
# ADD TO CART (SAFE)
# =========================
@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get("cart", {})
    pid = str(product.id)

    qty = int(request.POST.get("quantity", 1))

    # 🔒 STOCK ENFORCEMENT
    if product.stock <= 0:
        return redirect("cart:cart_detail")

    current_qty = cart.get(pid, 0)
    new_qty = min(current_qty + qty, product.stock)

    cart[pid] = new_qty
    request.session["cart"] = cart

    return redirect("cart:cart_detail")


# =========================
# REMOVE ITEM (POST ONLY)
# =========================
@login_required
def cart_remove(request, product_id):
    if request.method != "POST":
        return redirect("cart:cart_detail")

    cart = request.session.get("cart", {})
    pid = str(product_id)

    cart.pop(pid, None)
    request.session["cart"] = cart

    return redirect("cart:cart_detail")


# =========================
# UPDATE CART (+ / −)
# =========================
@login_required
def cart_update(request, product_id):
    if request.method != "POST":
        return redirect("cart:cart_detail")

    cart = request.session.get("cart", {})
    product = get_object_or_404(Product, id=product_id)
    pid = str(product.id)

    current_qty = cart.get(pid, 0)
    action = request.POST.get("action")

    if action == "inc" and current_qty < product.stock:
        cart[pid] = current_qty + 1

    elif action == "dec":
        if current_qty > 1:
            cart[pid] = current_qty - 1
        else:
            cart.pop(pid, None)

    request.session["cart"] = cart
    return redirect("cart:cart_detail")