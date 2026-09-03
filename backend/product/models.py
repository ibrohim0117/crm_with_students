from django.db import models
from django.db.models import UniqueConstraint
from django.contrib.postgres.indexes import GinIndex
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        constraints = [
            UniqueConstraint(
                fields=['parent', 'slug'], 
                name='unique_category_parent_slug'
            )
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=50)        # masalan: Kilogramm
    short_name = models.CharField(max_length=15)   # masalan: kg
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.short_name})"


class Product(models.Model):
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='products')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    min_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta:
    #     indexes = [
    #         models.Index(fields=['is_active', 'category']),
    #         models.Index(fields=['slug']),
    #         GinIndex(fields=['name'], name='product_name_gin_idx', opclasses=['gin_trgm_ops']),
    #     ]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(product=self.product, is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - Image ({self.pk})"