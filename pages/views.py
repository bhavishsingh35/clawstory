from django.shortcuts import render, get_object_or_404
from .models import Collection,Product

def home(request):
    return render(request,"pages/home.html")

def shop(request):
    products = Product.objects.all()
    return render(request, "pages/shop.html", {"products": products})

def contact(request):
    return render(request,"pages/contact.html")

def collection_list(request):
    collections = Collection.objects.all()
    return render(request, "pages/collections.html", {
        "collections": collections
    })

def collection_detail(request, slug):
    collection = get_object_or_404(Collection, slug=slug)
    products = collection.products.all()
    return render(
        request,
        "pages/collection_detail.html",
        {
            "collection": collection,
            "products": products
        }
    )

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(
        request,
        "pages/product_detail.html",
        {"product": product}
    )