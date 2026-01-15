from django.contrib import admin
from django.utils.html import format_html
from .models import Collection, Product


# =========================
# COLLECTION ADMIN
# =========================
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "image_preview",
    )

    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    readonly_fields = ("image_preview",)

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "slug"),
        }),
        ("Collection Image", {
            "fields": ("image", "image_preview"),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Preview"


# =========================
# PRODUCT ADMIN
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "collection",
        "price",
        "stock",
        "image_preview",
    )

    list_filter = ("collection", "stock")
    search_fields = ("name", "collection__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    readonly_fields = ("image_preview",)

    fieldsets = (
        ("Basic Information", {
            "fields": ("collection", "name", "slug"),
        }),
        ("Pricing & Inventory", {
            "fields": ("price", "stock"),
        }),
        ("Description", {
            "fields": ("description",),
        }),
        ("Product Image", {
            "fields": ("image", "image_preview"),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Preview"