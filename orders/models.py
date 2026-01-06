from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Order(models.Model):

    STATUS_CHOICES = [
        ("PLACED", "Placed"),
        ("PAYMENT_PENDING", "Payment Pending"),
        ("CONFIRMED", "Confirmed"),
        ("DISPATCHED", "Dispatched"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    PAYMENT_METHODS = [
        ("COD", "Cash on Delivery"),
        ("ONLINE", "Online Payment"),
    ]

    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    total = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="PENDING"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PLACED"
    )

    payment_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_payment_expired(self):
        if self.payment_expires_at:
            return timezone.now() > self.payment_expires_at
        return False

    def _str_(self):
        return f"Order #{self.id} - {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        "pages.Product",
        on_delete=models.PROTECT
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def _str_(self):
        return f"{self.product.name} x {self.quantity}"