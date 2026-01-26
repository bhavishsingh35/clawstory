from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.views.decorators.http import require_GET

from .models import Collection, Product


# =====================================================
# HOME PAGE
# =====================================================
@require_GET
def home(request):
    """
    Homepage:
    - Featured + latest products
    - Search support
    - SEO-optimized metadata
    """

    query = request.GET.get("q", "").strip()

    products_qs = (
        Product.objects
        .select_related("collection")
        .filter(is_active=True)
        .only(
            "id",
            "name",
            "slug",
            "price",
            "image",
            "collection__slug",
            "collection__name",
            "created_at",
            "is_featured",
        )
        .order_by("-is_featured", "-created_at")
    )

    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    collections = (
        Collection.objects
        .filter(is_active=True)
        .only("id", "name", "slug", "image")
        .order_by("name")
    )

    context = {
        "products": products_qs[:8],
        "collections": collections,
        "query": query,
        "page_title": "ClawStory – Premium Fashion Store",
        "meta_description": (
            "Shop premium fashion at ClawStory. "
            "Discover trending collections, quality apparel, "
            "and modern designs for men and women."
        ),
        "meta_robots": "index,follow",
    }

    return render(request, "pages/home.html", context)


# =====================================================
# SHOP PAGE
# =====================================================
@require_GET
def shop(request):
    """
    Product listing page with pagination and search.
    """

    query = request.GET.get("q", "").strip()

    products_qs = (
        Product.objects
        .select_related("collection")
        .filter(is_active=True)
        .only(
            "id",
            "name",
            "slug",
            "price",
            "image",
            "collection__slug",
            "collection__name",
            "created_at",
        )
        .order_by("-created_at")
    )

    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        "products": page_obj,
        "query": query,
        "page_title": "Shop – ClawStory",
        "meta_description": (
            "Browse all products at ClawStory. "
            "Premium clothing, modern styles, and exclusive collections."
        ),
        "meta_robots": "index,follow",
    }

    return render(request, "pages/shop.html", context)


# =====================================================
# COLLECTION LIST
# =====================================================
@require_GET
def collection_list(request):
    """
    List of all active collections.
    """

    collections = (
        Collection.objects
        .filter(is_active=True)
        .only("id", "name", "slug", "image")
        .order_by("name")
    )

    context = {
        "collections": collections,
        "page_title": "Collections – ClawStory",
        "meta_description": (
            "Explore curated fashion collections at ClawStory. "
            "Find styles designed for every occasion."
        ),
        "meta_robots": "index,follow",
    }

    return render(request, "pages/collections.html", context)


# =====================================================
# COLLECTION DETAIL
# =====================================================
@require_GET
def collection_detail(request, slug):
    """
    Product list within a collection.
    """

    collection = get_object_or_404(
        Collection,
        slug=slug,
        is_active=True
    )

    products_qs = (
        collection.products
        .filter(is_active=True)
        .select_related("collection")
        .only(
            "id",
            "name",
            "slug",
            "price",
            "image",
            "collection__slug",
            "collection__name",
            "created_at",
        )
        .order_by("-created_at")
    )

    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        "collection": collection,
        "products": page_obj,
        "page_title": f"{collection.name} – ClawStory",
        "meta_description": (
            f"Shop {collection.name} collection at ClawStory. "
            "Premium quality apparel and modern designs."
        ),
        "meta_robots": "index,follow",
    }

    return render(request, "pages/collection_detail.html", context)


# =====================================================
# PRODUCT DETAIL
# =====================================================
@require_GET
def product_detail(request, collection_slug, product_slug):
    """
    Individual product detail page.
    """

    product = get_object_or_404(
        Product.objects.select_related("collection"),
        collection__slug=collection_slug,
        slug=product_slug,
        is_active=True
    )

    related_products = (
        Product.objects
        .filter(
            collection=product.collection,
            is_active=True
        )
        .exclude(id=product.id)
        .only(
            "id",
            "name",
            "slug",
            "price",
            "image",
            "created_at",
        )
        .order_by("-created_at")[:4]
    )

    meta_description = (
        product.description[:160]
        if product.description
        else f"Buy {product.name} at ClawStory. Premium quality fashion."
    )

    context = {
        "product": product,
        "related_products": related_products,
        "page_title": f"{product.name} – ClawStory",
        "meta_description": meta_description,
        "meta_robots": "index,follow",
    }

    return render(request, "pages/product_detail.html", context)


# =====================================================
# STATIC PAGES (GET ONLY)
# =====================================================
@require_GET
def contact(request):
    return render(request, "pages/contact.html")


@require_GET
def help_center(request):
    return render(request, "pages/help_center.html")


@require_GET
def returns(request):
    return render(request, "pages/returns.html")


@require_GET
def track_order(request):
    return render(request, "pages/track_order.html")


@require_GET
def about_us(request):
    return render(request, "pages/about_us.html")


@require_GET
def careers(request):
    return render(request, "pages/careers.html")


@require_GET
def privacy_policy(request):
    return render(request, "pages/privacy_policy.html")


@require_GET
def terms_conditions(request):
    return render(request, "pages/terms_conditions.html")
