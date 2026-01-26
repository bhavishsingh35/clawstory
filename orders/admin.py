from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Order,
    OrderItem,
    PaymentTransaction,
    WebhookEvent,
)


# ==================================================
# ORDER ITEM INLINE (READ-ONLY SNAPSHOT)
# ==================================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fk_name = "order"

    readonly_fields = (
        "product",
        "product_name",
        "product_sku",
        "product_slug",
        "product_image_preview",
        "price",
        "quantity",
        "line_total_display",
    )

    fields = (
        "product",
        "product_name",
        "product_sku",
        "product_slug",
        "product_image_preview",
        "price",
        "quantity",
        "line_total_display",
    )

    def line_total_display(self, obj):
        return f"₹ {obj.line_total:.2f}"

    line_total_display.short_description = "Subtotal"

    def product_image_preview(self, obj):
        if obj.product_image:
            return format_html(
                '<img src="{}" style="height:60px; border-radius:6px;" />',
                obj.product_image,
            )
        return "—"

    product_image_preview.short_description = "Image"


# ==================================================
# ORDER ADMIN (PRIMARY OPS VIEW)
# ==================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "colored_status",
        "display_total",
        "currency",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "order_number",
        "user__username",
        "user__email",
    )

    ordering = ("-created_at",)
    inlines = [OrderItemInline]

    readonly_fields = (
        "id",
        "order_number",
        "user",
        "subtotal",
        "shipping_charge",
        "tax",
        "discount",
        "total_amount",
        "currency",
        "stock_locked",
        "stock_restored",
        "refund_processed",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Order",
            {
                "fields": (
                    "order_number",
                    "user",
                    "status",
                )
            },
        ),
        (
            "Shipping Snapshot",
            {
                "fields": (
                    "full_name",
                    "phone",
                    "address_line",
                    "city",
                    "state",
                    "pincode",
                    "country",
                )
            },
        ),
        (
            "Financial Snapshot (Locked)",
            {
                "fields": (
                    "subtotal",
                    "shipping_charge",
                    "tax",
                    "discount",
                    "total_amount",
                    "currency",
                )
            },
        ),
        (
            "System Flags",
            {
                "fields": (
                    "stock_locked",
                    "stock_restored",
                    "refund_processed",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # --------------------------------------------------
    # DISPLAY HELPERS
    # --------------------------------------------------
    def display_total(self, obj):
        return f"₹ {obj.total_amount:.2f}"

    display_total.short_description = "Total"

    def colored_status(self, obj):
        color = {
            Order.CREATED: "#6b7280",
            Order.PAYMENT_PENDING: "#f59e0b",
            Order.PAYMENT_FAILED: "#dc2626",
            Order.PAID: "#16a34a",
            Order.PROCESSING: "#2563eb",
            Order.SHIPPED: "#0ea5e9",
            Order.DELIVERED: "#16a34a",
            Order.CANCEL_REQUESTED: "#f97316",
            Order.CANCELLED: "#dc2626",
            Order.REFUNDED: "#7c3aed",
        }.get(obj.status, "#374151")

        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    colored_status.short_description = "Order Status"


# ==================================================
# PAYMENT TRANSACTION ADMIN (STRIPE / AUDIT)
# ==================================================
@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "gateway",
        "status",
        "amount",
        "currency",
        "created_at",
    )

    list_filter = ("gateway", "status", "created_at")
    search_fields = ("intent_id", "charge_id", "idempotency_key")

    readonly_fields = (
        "id",
        "order",
        "gateway",
        "intent_id",
        "client_secret",
        "charge_id",
        "amount",
        "currency",
        "status",
        "idempotency_key",
        "raw_response",
        "created_at",
    )

    ordering = ("-created_at",)


# ==================================================
# WEBHOOK EVENT ADMIN (REPLAY-SAFE LOG)
# ==================================================
@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "gateway",
        "event_id",
        "event_type",
        "linked_order",
        "processed",
        "received_at",
    )

    list_filter = ("gateway", "event_type", "processed", "received_at")
    search_fields = ("event_id",)

    readonly_fields = (
        "id",
        "gateway",
        "event_id",
        "event_type",
        "order",
        "payload",
        "processed",
        "processed_at",
        "received_at",
    )

    ordering = ("-received_at",)

    def linked_order(self, obj):
        return obj.order.order_number if obj.order else "—"

    linked_order.short_description = "Order"
