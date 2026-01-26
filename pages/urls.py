from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    # =========================
    # HOME
    # =========================
    path(
        "",
        views.home,
        name="home"
    ),

    # =========================
    # SHOP / CATALOG
    # =========================
    path(
        "shop/",
        views.shop,
        name="shop"
    ),

    # =========================
    # COLLECTIONS
    # =========================
    path(
        "collections/",
        views.collection_list,
        name="collection_list"
    ),
    path(
        "collections/<slug:slug>/",
        views.collection_detail,
        name="collection_detail"
    ),

    # =========================
    # PRODUCT DETAIL
    # SEO-SAFE & SCALE-READY
    # =========================
    path(
        "collections/<slug:collection_slug>/<slug:product_slug>/",
        views.product_detail,
        name="product_detail"
    ),

    # =========================
    # STATIC / MARKETING PAGES
    # =========================
    path(
        "contact/",
        views.contact,
        name="contact"
    ),
    path(
        "help-center/",
        views.help_center,
        name="help_center"
    ),
    path(
        "returns/",
        views.returns,
        name="returns"
    ),
    path(
        "track-order/",
        views.track_order,
        name="track_order"
    ),
    path(
        "about-us/",
        views.about_us,
        name="about_us"
    ),
    path(
        "careers/",
        views.careers,
        name="careers"
    ),

    # =========================
    # LEGAL / POLICY PAGES
    # =========================
    path(
        "privacy-policy/",
        views.privacy_policy,
        name="privacy_policy"
    ),
    path(
        "terms-conditions/",
        views.terms_conditions,
        name="terms_conditions"
    ),
]
