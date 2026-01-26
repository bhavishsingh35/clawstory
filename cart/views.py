from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from pages.models import Product


# =====================================================
# CART UTILS (CENTRALIZED, SAFE)
# =====================================================
def _get_cart(session):
    """
    Cart structure (SESSION ONLY, NOT SOURCE OF TRUTH):

    {
        "product_id": {
            "qty": int,
            "price": "decimal as string"   # snapshot for display only
        }
    }
    """
    return session.setdefault("cart", {})


def _save_cart(session, cart):
    session["cart"] = cart
    session.modified = True


# =====================================================
# CART DETAIL
# =====================================================
def cart_detail(request):
    cart = _get_cart(request.session)

    product_ids = list(cart.keys())
    products = Product.objects.filter(
        id__in=product_ids,
        is_active=True
    )

    cart_items = []
    total = Decimal("0.00")
    updated = False

    for product in products:
        pid = str(product.id)
        item = cart.get(pid)

        if not item:
            continue

        try:
            qty = int(item.get("qty", 0))
        except (TypeError, ValueError):
            cart.pop(pid, None)
            updated = True
            continue

        # Defensive cleanup
        if qty <= 0:
            cart.pop(pid, None)
            updated = True
            continue

        # Clamp to available stock (best-effort)
        if product.stock <= 0:
            cart.pop(pid, None)
            updated = True
            continue

        if qty > product.stock:
            qty = product.stock
            item["qty"] = qty
            updated = True

        # Price is DISPLAY ONLY
        try:
            price = Decimal(item.get("price"))
        except Exception:
            price = product.price
            item["price"] = str(product.price)
            updated = True

        subtotal = price * qty
        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": qty,
            "price": price,
            "subtotal": subtotal,
        })

    if updated:
        _save_cart(request.session, cart)

    return render(
        request,
        "cart/cart.html",
        {
            "cart_items": cart_items,
            "total": total,
        }
    )


# =====================================================
# ADD TO CART
# =====================================================
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    cart = _get_cart(request.session)
    pid = str(product.id)

    try:
        qty = int(request.POST.get("qty", 1))
    except (TypeError, ValueError):
        qty = 1

    if qty <= 0:
        return redirect("cart:cart_detail")

    # Defensive cap (prevents abuse)
    qty = min(qty, 10)

    if not product.can_fulfill(1):
        return redirect(
            "pages:product_detail",
            collection_slug=product.collection.slug,
            product_slug=product.slug,
        )

    current = cart.get(pid, {})
    current_qty = int(current.get("qty", 0))

    final_qty = min(current_qty + qty, product.stock)

    cart[pid] = {
        "qty": final_qty,
        # Snapshot price (DISPLAY ONLY)
        "price": str(product.price),
    }

    _save_cart(request.session, cart)

    # BUY NOW shortcut
    if request.POST.get("action") == "buy":
        return redirect("orders:checkout")

    return redirect("cart:cart_detail")


# =====================================================
# REMOVE ITEM
# =====================================================
@require_POST
def cart_remove(request, product_id):
    cart = _get_cart(request.session)
    cart.pop(str(product_id), None)
    _save_cart(request.session, cart)

    return redirect("cart:cart_detail")


# =====================================================
# UPDATE CART (INCREMENT / DECREMENT)
# =====================================================
@require_POST
def cart_update(request, product_id):
    cart = _get_cart(request.session)
    pid = str(product_id)

    item = cart.get(pid)
    if not item:
        return redirect("cart:cart_detail")

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    action = request.POST.get("action")

    try:
        qty = int(item.get("qty", 0))
    except (TypeError, ValueError):
        cart.pop(pid, None)
        _save_cart(request.session, cart)
        return redirect("cart:cart_detail")

    if action == "inc":
        if product.can_fulfill(qty + 1):
            item["qty"] = qty + 1

    elif action == "dec":
        if qty > 1:
            item["qty"] = qty - 1
        else:
            cart.pop(pid, None)

    _save_cart(request.session, cart)
    return redirect("cart:cart_detail")
