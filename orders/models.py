from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


# =========================
# ORDER
# =========================
class Order(models.Model):
    # -------- ORDER STATUS --------
    STATUS_CREATED = "CREATED"
    STATUS_PAYMENT_PENDING = "PAYMENT_PENDING"
    STATUS_PAID = "PAID"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_SHIPPED = "SHIPPED"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_PAYMENT_PENDING, "Payment Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_FAILED, "Failed"),
    ]

    # -------- PAYMENT --------
    PAYMENT_COD = "COD"
    PAYMENT_ONLINE = "ONLINE"

    PAYMENT_METHODS = [
        (PAYMENT_COD, "Cash on Delivery"),
        (PAYMENT_ONLINE, "Online Payment"),
    ]

    PAYMENT_PENDING = "PENDING"
    PAYMENT_SUCCESS = "SUCCESS"
    PAYMENT_FAILED = "FAILED"
    PAYMENT_REFUNDED = "REFUNDED"

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, "Pending"),
        (PAYMENT_SUCCESS, "Success"),
        (PAYMENT_FAILED, "Failed"),
        (PAYMENT_REFUNDED, "Refunded"),
    ]

    # -------- CORE --------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        db_index=True,
    )

    # -------- DELIVERY SNAPSHOT --------
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)

    address_line = models.TextField()
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=60)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50, default="India")

    # -------- FINANCIAL --------
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    currency = models.CharField(max_length=10, default="INR")

    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, db_index=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING,
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        db_index=True,
    )

    # -------- PAYMENT LIFECYCLE --------
    payment_attempts = models.PositiveIntegerField(default=0)
    payment_expires_at = models.DateTimeField(null=True, blank=True)

    # -------- GATEWAY (RAZORPAY) --------
    gateway = models.CharField(max_length=50, default="razorpay")

    razorpay_order_id = models.CharField(
        max_length=120, null=True, blank=True, unique=True, db_index=True
    )
    razorpay_payment_id = models.CharField(
        max_length=120, null=True, blank=True, db_index=True
    )
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)

    # -------- AUDIT --------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -------- BUSINESS RULES --------
    def mark_payment_pending(self, razorpay_order_id: str):
        self.status = self.STATUS_PAYMENT_PENDING
        self.payment_status = self.PAYMENT_PENDING
        self.payment_attempts += 1
        self.razorpay_order_id = razorpay_order_id
        self.payment_expires_at = timezone.now() + timezone.timedelta(minutes=15)
        self.save(
            update_fields=[
                "status",
                "payment_status",
                "payment_attempts",
                "razorpay_order_id",
                "payment_expires_at",
            ]
        )

    def mark_paid(self, payment_id: str, signature: str):
        self.status = self.STATUS_PAID
        self.payment_status = self.PAYMENT_SUCCESS
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.save(
            update_fields=[
                "status",
                "payment_status",
                "razorpay_payment_id",
                "razorpay_signature",
            ]
        )

    def mark_failed(self):
        self.status = self.STATUS_FAILED
        self.payment_status = self.PAYMENT_FAILED
        self.save(update_fields=["status", "payment_status"])

    def __str__(self):
        return f"Order {self.id}"


# =========================
# ORDER ITEM
# =========================
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE
    )
    product = models.ForeignKey("pages.Product", on_delete=models.PROTECT)

    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.price * Decimal(self.quantity)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"


# =========================
# PAYMENT TRANSACTION
# =========================
class PaymentTransaction(models.Model):
    STATUS_CREATED = "CREATED"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    order = models.ForeignKey(
        Order,
        related_name="transactions",
        on_delete=models.CASCADE
    )

    gateway = models.CharField(max_length=50, default="razorpay")

    gateway_order_id = models.CharField(max_length=120, db_index=True)
    gateway_payment_id = models.CharField(
        max_length=120, null=True, blank=True, db_index=True
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED
    )

    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.gateway} | {self.status} | {self.amount}"


# =========================
# RAZORPAY WEBHOOK LOG
# =========================
class RazorpayWebhookEvent(models.Model):
    event_id = models.CharField(max_length=150, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_type
