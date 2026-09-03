from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.core.exceptions import ValidationError
import re


class UserManager(BaseUserManager):
    def create_user(self, phone_number, email, full_name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Telefon raqami kiritilishi shart.")
        if not email:
            raise ValueError("Email kiritilishi shart.")
        if not full_name:
            raise ValueError("F.I.SH (full_name) kiritilishi shart.")

        email = self.normalize_email(email)
        user = self.model(
            phone_number=phone_number,
            email=email,
            full_name=full_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser is_staff=True bo\'lishi kerak.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser is_superuser=True bo\'lishi kerak.')

        return self.create_user(phone_number, email, full_name, password, **extra_fields)


def validate_phone_number(value):
    pattern = r'^\+998\d{9}$'
    if not re.match(pattern, value):
        raise ValidationError("Telefon raqami '+998901234567' formatida bo'lishi kerak.")


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ADMIN = 'admin', 'Admin'

    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(
        max_length=13, 
        unique=True, 
        validators=[validate_phone_number]
    )
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.CharField(
        max_length=10, 
        choices=Role.choices, 
        default=Role.USER
    )
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    telegram_id = models.BigIntegerField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email', 'full_name']

    def save(self, *args, **kwargs):
        # 'role' admin bo'lsa, is_staff avtomatik True bo'ladi
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class VerificationCode(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = 'register', 'Register'
        RESET_PASSWORD = 'reset_password', 'Reset Password'

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='codes'
    )
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.user.phone_number} - {self.code} ({self.purpose})"