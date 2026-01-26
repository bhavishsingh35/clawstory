from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    # =====================================================
    # CART DISPLAY (READ-ONLY)
    # =====================================================
    path(
        "",
        views.cart_detail,
        name="cart_detail"
    ),

    # =====================================================
    # CART MUTATIONS (POST ONLY)
    # =====================================================
    path(
        "add/<int:product_id>/",
        views.cart_add,
        name="cart_add"
    ),
    path(
        "update/<int:product_id>/",
        views.cart_update,
        name="cart_update"
    ),
    path(
        "remove/<int:product_id>/",
        views.cart_remove,
        name="cart_remove"
    ),
]
