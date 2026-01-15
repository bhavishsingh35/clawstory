from django.db import models
from cloudinary.models import CloudinaryField
from django.utils import timezone


class Collection(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

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

    def _str_(self):
        return self.name


class Product(models.Model):
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="products"
    )

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    price = models.PositiveIntegerField()
    description = models.TextField(blank=True)

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

    stock = models.PositiveIntegerField(default=0)

    # ✅ CRITICAL: fixes migration + future features
    created_at = models.DateTimeField(default=timezone.now)

    def _str_(self):
        return self.name