from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # Checkout & Order
    path("checkout/", views.checkout, name="checkout"),
    path("create/", views.create_order, name="create_order"),

    # Payment flow (NEW – Amazon style)
    path("payment/<int:order_id>/", views.payment_page, name="payment"),
    path("payment/success/<int:order_id>/", views.payment_success, name="payment_success"),
    path("payment/failed/<int:order_id>/", views.payment_failed, name="payment_failed"),

    # Order success & history
    path("success/<int:order_id>/", views.order_success, name="order_success"),
    path("my-orders/", views.my_orders, name="my_orders"),
]