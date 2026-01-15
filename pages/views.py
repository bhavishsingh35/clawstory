from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Collection, Product


# =========================
# HOME PAGE
# =========================
def home(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.select_related("collection").order_by("-created_at")

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    collections = Collection.objects.all().order_by("name")

    context = {
        "products": products[:8],  # latest 8 for homepage
        "collections": collections,
        "query": query,
        "page_title": "ClawStory – Premium Fashion Store",
        "meta_description": "Shop premium fashion collections at ClawStory. Discover trending styles, quality apparel, and modern designs.",
    }

    return render(request, "pages/home.html", context)


# =========================
# SHOP PAGE (ALL PRODUCTS)
# =========================
def shop(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("collection").order_by("-created_at")

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "products": page_obj,
        "query": query,
        "page_title": "Shop – ClawStory",
        "meta_description": "Browse all products at ClawStory. Premium clothing, modern styles, and exclusive collections.",
    }

    return render(request, "pages/shop.html", context)


# =========================
# COLLECTION LIST
# =========================
def collection_list(request):
    collections = Collection.objects.all().order_by("name")

    context = {
        "collections": collections,
        "page_title": "Collections – ClawStory",
        "meta_description": "Explore fashion collections at ClawStory. Handpicked styles for every occasion.",
    }

    return render(request, "pages/collections.html", context)


# =========================
# COLLECTION DETAIL
# =========================
def collection_detail(request, slug):
    collection = get_object_or_404(Collection, slug=slug)

    products = collection.products.all().order_by("-created_at")

    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "collection": collection,
        "products": page_obj,
        "page_title": f"{collection.name} – ClawStory",
        "meta_description": f"Shop {collection.name} collection at ClawStory. Premium quality and modern designs.",
    }

    return render(request, "pages/collection_detail.html", context)


# =========================
# PRODUCT DETAIL
# =========================
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("collection"),
        slug=slug
    )

    related_products = (
        Product.objects
        .filter(collection=product.collection)
        .exclude(id=product.id)
        .order_by("-created_at")[:4]
    )

    context = {
        "product": product,
        "related_products": related_products,
        "page_title": f"{product.name} – ClawStory",
        "meta_description": product.description[:160] if product.description else f"Buy {product.name} at ClawStory.",
    }

    return render(request, "pages/product_detail.html", context)


# =========================
# CONTACT PAGE
# =========================
def contact(request):
    context = {
        "page_title": "Contact Us – ClawStory",
        "meta_description": "Contact ClawStory for support, queries, or assistance regarding your orders.",
    }

    return render(request, "pages/contact.html", context)