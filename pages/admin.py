from django.contrib import admin, messages
from django.db import transaction
from django.db.models import F
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Collection, Product


# =====================================================
# COLLECTION ADMIN
# =====================================================
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "image_preview",
        "created_at",
    )

    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    readonly_fields = ("image_preview", "created_at")

    fieldsets = (
        (_("Basic Information"), {
            "fields": ("name", "slug", "is_active"),
        }),
        (_("Collection Image"), {
            "fields": ("image", "image_preview"),
        }),
        (_("System Metadata"), {
            "fields": ("created_at",),
        }),
    )

    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;'
                'object-fit:cover;border-radius:8px;" />',
                obj.image_url
            )
        return "—"

    image_preview.short_description = "Preview"

    # Prevent accidental bulk deletion
    actions = None


# =====================================================
# PRODUCT ADMIN
# =====================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "collection",
        "price",
        "stock",
        "is_active",
        "is_featured",
        "image_preview",
        "created_at",
    )

    list_filter = (
        "collection",
        "is_active",
        "is_featured",
    )

    search_fields = (
        "name",
        "slug",
        "collection__name",
    )

    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-created_at",)
    list_select_related = ("collection",)

    readonly_fields = (
        "image_preview",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (_("Basic Information"), {
            "fields": ("collection", "name", "slug", "is_active", "is_featured"),
        }),
        (_("Pricing & Inventory"), {
            "fields": ("price", "stock"),
        }),
        (_("Description"), {
            "fields": ("description",),
        }),
        (_("Product Image"), {
            "fields": ("image", "image_preview"),
        }),
        (_("System Metadata"), {
            "fields": ("created_at", "updated_at"),
        }),
    )

    # -------------------------
    # QUERY OPTIMIZATION
    # -------------------------
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("collection")

    # -------------------------
    # IMAGE PREVIEW
    # -------------------------
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;'
                'object-fit:cover;border-radius:8px;" />',
                obj.image_url
            )
        return "—"

    image_preview.short_description = "Preview"

    # -------------------------
    # SAFE ADMIN ACTIONS
    # -------------------------
    actions = [
        "mark_active",
        "mark_inactive",
        "mark_featured",
        "mark_unfeatured",
        "increase_stock_by_10",
    ]

    @admin.action(description="Mark selected products as active")
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} products marked as active.",
            level=messages.SUCCESS
        )

    @admin.action(description="Mark selected products as inactive")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} products marked as inactive.",
            level=messages.WARNING
        )

    @admin.action(description="Mark selected products as featured")
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(
            request,
            f"{updated} products marked as featured.",
            level=messages.SUCCESS
        )

    @admin.action(description="Remove featured flag")
    def mark_unfeatured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(
            request,
            f"{updated} products unfeatured.",
            level=messages.INFO
        )

    @admin.action(description="Increase stock by 10 (inventory-safe)")
    def increase_stock_by_10(self, request, queryset):
        """
        Explicitly safe admin stock increase.
        Uses DB-level constraints as final guard.
        """
        with transaction.atomic():
            updated = queryset.update(stock=F("stock") + 10)

        self.message_user(
            request,
            f"Stock increased by 10 for {updated} products.",
            level=messages.SUCCESS
        )

    # -------------------------
    # PERMISSION HARDENING
    # -------------------------
    def has_delete_permission(self, request, obj=None):
        """
        Disable delete in admin UI.
        Soft-delete via is_active only.
        """
        return False

    def get_readonly_fields(self, request, obj=None):
        """
        Prevent non-superusers from editing stock directly.
        """
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly.append("stock")
        return readonly
