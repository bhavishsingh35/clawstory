from decimal import Decimal

from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse
from django.core.validators import MinValueValidator
from cloudinary.models import CloudinaryField


# =====================================================
# COLLECTION MODEL
# =====================================================
class Collection(models.Model):
    """
    Product grouping / category model.
    Designed for SEO, admin control, and future scalability.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Public name of the collection"
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="SEO-friendly URL identifier"
    )

    image = CloudinaryField(
        "image",
        transformation=[{
            "width": 600,
            "height": 600,
            "crop": "fill",
            "gravity": "auto",
            "quality": "auto",
            "fetch_format": "auto"
        }],
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Disable to hide collection without deleting data"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Collection"
        verbose_name_plural = "Collections"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse(
            "pages:collection_detail",
            kwargs={"slug": self.slug}
        )

    @property
    def image_url(self) -> str:
        """
        Safe image accessor for templates & admin.
        """
        return self.image.url if self.image else ""


# =====================================================
# PRODUCT MODEL (CORE BUSINESS ENTITY)
# =====================================================
class Product(models.Model):
    """
    Core product model.
    Safe for payments, inventory, SEO, and scaling.
    """

    collection = models.ForeignKey(
        Collection,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="Collection this product belongs to"
    )

    name = models.CharField(
        max_length=150,
        help_text="Public product name"
    )

    slug = models.SlugField(
        max_length=160,
        db_index=True,
        help_text="SEO-friendly product URL slug"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Selling price in INR"
    )

    description = models.TextField(
        blank=True,
        help_text="Detailed product description (SEO-friendly)"
    )

    image = CloudinaryField(
        "image",
        transformation=[{
            "width": 600,
            "height": 600,
            "crop": "fill",
            "gravity": "auto",
            "quality": "auto",
            "fetch_format": "auto"
        }],
        blank=True,
        null=True
    )

    stock = models.PositiveIntegerField(
        default=0,
        help_text="Available inventory count"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Disable to hide product without deleting"
    )

    is_featured = models.BooleanField(
        default=False,
        help_text="Highlight on homepage or promotions"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "slug"],
                name="unique_product_slug_per_collection"
            ),
            # 🔒 DATABASE-LEVEL GUARANTEE: STOCK CAN NEVER BE NEGATIVE
            models.CheckConstraint(
                condition=Q(stock__gte=0),
                name="stock_never_negative"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse(
            "pages:product_detail",
            kwargs={
                "collection_slug": self.collection.slug,
                "product_slug": self.slug,
            }
        )

    # ------------------------------------------------------------------
    # INVENTORY & BUSINESS LOGIC (PRODUCTION SAFE)
    # ------------------------------------------------------------------

    def is_in_stock(self) -> bool:
        """
        Simple availability check (used for listings).
        """
        return self.is_active and self.stock > 0

    def can_fulfill(self, quantity: int) -> bool:
        """
        Cart / checkout validation helper.
        """
        return (
            self.is_active
            and quantity > 0
            and self.stock >= quantity
        )

    @transaction.atomic
    def reduce_stock(self, quantity: int) -> None:
        """
        Safe stock reduction.
        MUST be called during order creation inside atomic blocks.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        product = (
            Product.objects
            .select_for_update()
            .only("id", "stock")
            .get(pk=self.pk)
        )

        if product.stock < quantity:
            raise ValueError("Insufficient stock")

        product.stock -= quantity
        product.save(update_fields=["stock"])

    @transaction.atomic
    def increase_stock(self, quantity: int) -> None:
        """
        Used for refunds, cancellations, restocks.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        product = (
            Product.objects
            .select_for_update()
            .only("id", "stock")
            .get(pk=self.pk)
        )

        product.stock += quantity
        product.save(update_fields=["stock"])

    @property
    def image_url(self) -> str:
        """
        Safe image accessor for templates, order history & admin.
        """
        return self.image.url if self.image else ""
