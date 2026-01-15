from django.contrib import admin
from .models import (
    Order,
    OrderItem,
    PaymentTransaction,
    RazorpayWebhookEvent,
)


# ==================================================
# ORDER ITEM INLINE
# ==================================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product",
        "product_name",
        "price",
        "quantity",
        "subtotal_display",
    )

    def subtotal_display(self, obj):
        return f"₹ {obj.subtotal}"

    subtotal_display.short_description = "Subtotal"


# ==================================================
# ORDER ADMIN
# ==================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "payment_method",
        "payment_status",
        "status",
        "display_total",
        "payment_attempts",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "payment_status",
        "created_at",
    )

    search_fields = (
        "id",
        "user__username",
        "user__email",
        "razorpay_order_id",
        "razorpay_payment_id",
    )

    readonly_fields = (
        "id",
        "user",
        "subtotal",
        "shipping_charge",
        "tax",
        "total_amount",
        "currency",
        "payment_attempts",
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        "payment_expires_at",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)
    inlines = [OrderItemInline]

    fieldsets = (
        (
            "Order",
            {
                "fields": (
                    "id",
                    "user",
                    "status",
                    "payment_status",
                    "payment_method",
                )
            },
        ),
        (
            "Amounts",
            {
                "fields": (
                    "subtotal",
                    "shipping_charge",
                    "tax",
                    "total_amount",
                    "currency",
                )
            },
        ),
        (
            "Razorpay",
            {
                "fields": (
                    "razorpay_order_id",
                    "razorpay_payment_id",
                    "razorpay_signature",
                    "payment_attempts",
                    "payment_expires_at",
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

    def display_total(self, obj):
        return f"₹ {obj.total_amount}"

    display_total.short_description = "Total Amount"


# ==================================================
# PAYMENT TRANSACTION ADMIN
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

    list_filter = ("gateway", "status")
    search_fields = ("gateway_order_id", "gateway_payment_id")

    readonly_fields = (
        "order",
        "gateway",
        "gateway_order_id",
        "gateway_payment_id",
        "amount",
        "currency",
        "status",
        "raw_response",
        "created_at",
    )
    ordering = ("-created_at",)


# ==================================================
# RAZORPAY WEBHOOK EVENT ADMIN (AUDIT ONLY)
# ==================================================
@admin.register(RazorpayWebhookEvent)
class RazorpayWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "event_type",
        "processed",
        "received_at",
    )

    list_filter = ("event_type", "processed")
    search_fields = ("event_id",)
    readonly_fields = (
        "event_id",
        "event_type",
        "payload",
        "processed",
        "received_at",
    )

    ordering = ("-received_at",)
