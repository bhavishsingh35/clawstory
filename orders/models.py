from decimal import Decimal
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from pages.models import Product


# =====================================================
# ORDER (CANONICAL AGGREGATE ROOT)
# =====================================================
class Order(models.Model):
    """
    Canonical Order.
    Single source of truth for:
    - lifecycle
    - inventory state
    - refund state
    """

    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

    STATUS_CHOICES = [
        (CREATED, "Created"),
        (PAYMENT_PENDING, "Payment Pending"),
        (PAYMENT_FAILED, "Payment Failed"),
        (PAID, "Paid"),
        (PROCESSING, "Processing"),
        (SHIPPED, "Shipped"),
        (DELIVERED, "Delivered"),
        (CANCEL_REQUESTED, "Cancel Requested"),
        (CANCELLED, "Cancelled"),
        (REFUNDED, "Refunded"),
    ]

    VALID_TRANSITIONS = {
        CREATED: {PAYMENT_PENDING, CANCELLED},
        PAYMENT_PENDING: {PAID, PAYMENT_FAILED, CANCELLED},
        PAYMENT_FAILED: {PAYMENT_PENDING, CANCELLED},
        PAID: {PROCESSING, CANCEL_REQUESTED, REFUNDED},
        PROCESSING: {SHIPPED, CANCEL_REQUESTED},
        CANCEL_REQUESTED: {CANCELLED, REFUNDED},
        SHIPPED: {DELIVERED},
        DELIVERED: set(),
        CANCELLED: set(),
        REFUNDED: set(),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order_number = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # Shipping snapshot
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)

    address_line = models.TextField()
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=60)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50, default="India")

    # Financial snapshot
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    currency = models.CharField(max_length=10, default="INR")

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=CREATED,
        db_index=True,
    )

    # Idempotency guards
    stock_locked = models.BooleanField(default=False)
    stock_restored = models.BooleanField(default=False)
    refund_processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_order_number():
        date_part = timezone.now().strftime("%Y%m")
        random_part = uuid.uuid4().hex[:6].upper()
        return f"CS-{date_part}-{random_part}"

    def transition(self, to_state: str):
        allowed = self.VALID_TRANSITIONS.get(self.status, set())
        if to_state not in allowed:
            raise ValueError(f"Invalid order transition {self.status} → {to_state}")

        self.status = to_state
        self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return self.order_number


# =====================================================
# ORDER ITEM (IMMUTABLE SNAPSHOT)
# =====================================================
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100)
    product_slug = models.CharField(max_length=255)

    # Snapshot image URL (never depend on Product later)
    product_image = models.URLField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=["product_sku"]),
        ]

    @property
    def line_total(self):
        return (self.price or 0) * (self.quantity or 0)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"


# =====================================================
# PAYMENT TRANSACTION (GATEWAY AUDIT)
# =====================================================
class PaymentTransaction(models.Model):
    CREATED = "CREATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

    STATUS_CHOICES = [
        (CREATED, "Created"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(
        Order,
        related_name="payments",
        on_delete=models.CASCADE,
    )

    gateway = models.CharField(max_length=50)

    intent_id = models.CharField(max_length=150, blank=True, db_index=True)
    client_secret = models.CharField(max_length=255, blank=True)

    charge_id = models.CharField(max_length=150, null=True, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=CREATED,
        db_index=True,
    )

    idempotency_key = models.CharField(max_length=255, db_index=True)

    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.gateway} | {self.status} | {self.amount}"


# =====================================================
# WEBHOOK EVENT LOG (REPLAY-SAFE)
# =====================================================
class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    gateway = models.CharField(max_length=50)
    event_id = models.CharField(max_length=150, unique=True)
    event_type = models.CharField(max_length=100)

    order = models.ForeignKey(
        Order,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-received_at",)
        indexes = [
            models.Index(fields=["gateway"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["processed"]),
        ]

    def __str__(self):
        return f"{self.gateway} | {self.event_type}"
