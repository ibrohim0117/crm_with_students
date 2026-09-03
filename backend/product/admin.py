from django.contrib import admin
from .models import Category, Unit, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'is_main', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'created_at')
    search_fields = ('name', 'short_name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'category', 
        'price', 
        'discount_price', 
        'quantity', 
        'unit', 
        'sku', 
        'views_count', 
        'is_active', 
        'created_at'
    )
    list_filter = ('is_active', 'category', 'unit', 'created_at')
    search_fields = ('name', 'sku', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('views_count', 'created_at', 'updated_at')
    inlines = [ProductImageInline]
    raw_id_fields = ('created_by', 'category')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'sku', 'description', 'is_active')
        }),
        ('Narxlar va Ombor', {
            'fields': ('price', 'discount_price', 'cost_price', 'quantity', 'min_quantity', 'unit')
        }),
        ('Statistika va Muallif', {
            'fields': ('views_count', 'created_by', 'created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_main', 'created_at')
    list_filter = ('is_main', 'created_at')
    raw_id_fields = ('product',)