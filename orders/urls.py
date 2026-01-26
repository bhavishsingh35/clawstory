from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [

    # ==================================================
    # CHECKOUT & ORDER CREATION
    # ==================================================
    path(
        "checkout/",
        views.checkout,
        name="checkout",
    ),
    path(
        "create/",
        views.create_order,
        name="create_order",
    ),

    # ==================================================
    # PAYMENT FLOW (STRIPE)
    # ==================================================
    path(
        "payment/<uuid:order_id>/",
        views.payment,
        name="payment",
    ),
    path(
        "payment/failed/<uuid:order_id>/",
        views.payment_failed,
        name="payment_failed",
    ),

    # ==================================================
    # ORDER RESULTS & HISTORY
    # ==================================================
    path(
        "success/<uuid:order_id>/",
        views.order_success,
        name="order_success",
    ),
    path(
        "my-orders/",
        views.my_orders,
        name="my_orders",
    ),
    path(
        "order/<uuid:order_id>/",
        views.order_detail,
        name="order_detail",
    ),

    # ==================================================
    # ORDER LIFECYCLE ACTIONS (USER-SAFE)
    # ==================================================
    path(
        "order/<uuid:order_id>/cancel/",
        views.cancel_order,
        name="cancel_order",
    ),

    # ==================================================
    # WEBHOOKS (NON-USER FACING)
    # ==================================================
    path(
        "webhooks/stripe/",
        views.stripe_webhook,
        name="stripe_webhook",
    ),
]
