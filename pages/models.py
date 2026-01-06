from django.db import models


class Collection(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def _str_(self):
        return self.name


class Product(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    price = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)   # REQUIRED

    def _str_(self):
        return self.name