from django.db import transaction
from django.db.models import F


@transaction.atomic
def restore_inventory(order):
    """
    Restore inventory for an order.
    Safe to call multiple times (idempotent).
    """

    # 🛑 Idempotency guard
    if order.stock_restored:
        return

    # Lock order row
    order = (
        type(order)
        .objects
        .select_for_update()
        .get(pk=order.pk)
    )

    if order.stock_restored:
        return

    for item in order.items.select_related("product").select_for_update():
        product = item.product

        # Atomic increment
        product.stock = F("stock") + item.quantity
        product.save(update_fields=["stock"])

    order.stock_restored = True
    order.save(update_fields=["stock_restored"])


@transaction.atomic
def lock_inventory(order):
    """
    Lock (decrement) inventory when order is confirmed for payment.
    Safe to call multiple times.
    """

    # 🛑 Idempotency guard
    if order.stock_locked:
        return

    # Lock order row
    order = (
        type(order)
        .objects
        .select_for_update()
        .get(pk=order.pk)
    )

    if order.stock_locked:
        return

    for item in order.items.select_related("product").select_for_update():
        product = item.product

        if product.stock < item.quantity:
            raise ValueError(
                f"Insufficient stock for {product}"
            )

        # Atomic decrement
        product.stock = F("stock") - item.quantity
        product.save(update_fields=["stock"])

    order.stock_locked = True
    order.save(update_fields=["stock_locked"])
