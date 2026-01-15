from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [

    # ========================
    # CHECKOUT & ORDER CREATE
    # ========================
    path("checkout/", views.checkout, name="checkout"),
    path("create/", views.create_order, name="create_order"),

    # ========================
    # PAYMENT FLOW (RAZORPAY)
    # ========================
    path("payment/<uuid:order_id>/", views.payment, name="payment"),
    path("payment/failed/<uuid:order_id>/", views.payment_failed, name="payment_failed"),

    # ========================
    # ORDER RESULT
    # ========================
    path("success/<uuid:order_id>/", views.order_success, name="order_success"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("order/<uuid:order_id>/", views.order_detail, name="order_detail"),

    # ========================
    # RAZORPAY WEBHOOK (SOURCE OF TRUTH)
    # ========================
    path("webhooks/razorpay/", views.razorpay_webhook, name="razorpay_webhook"),
]
