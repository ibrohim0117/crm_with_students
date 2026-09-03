from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, VerificationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Admin panel ro'yxatida ko'rinadigan ustunlar
    list_display = ('phone_number', 'full_name', 'email', 'role', 'is_active', 'is_staff', 'telegram_id')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('phone_number', 'full_name', 'email', 'telegram_id')
    ordering = ('id',)

    # Foydalanuvchi ma'lumotlarini tahrirlash sahifasi guruhlari
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('full_name', 'email', 'bio', 'avatar', 'telegram_id')}),
        ('Huquqlar va Rol', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Muhim sanalar', {'fields': ('last_login', 'last_login_at')}),
    )

    # Yangi foydalanuvchi qo'shish sahifasi
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'email', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('last_login_at',)


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'purpose', 'is_used', 'attempts', 'expires_at', 'created_at')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('user__phone_number', 'user__full_name', 'code')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)