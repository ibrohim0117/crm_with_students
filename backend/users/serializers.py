import re

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .services import create_verification_code


def normalize_phone_number(value):
    """Telefon raqamni bitta '+998XXXXXXXXX' formatiga keltiradi."""
    if not value:
        return value
    digits = re.sub(r'\D', '', str(value))
    if digits.startswith('998'):
        digits = digits[3:]
    return f'+998{digits}'


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserSerializer(serializers.ModelSerializer):
    """`/auth/me/` uchun: GET — profil, PATCH — full_name, email, bio, avatar."""

    class Meta:
        model = User
        fields = (
            'id',
            'full_name',
            'phone_number',
            'email',
            'bio',
            'avatar',
            'role',
            'telegram_id',
            'is_active',
            'last_login_at',
        )
        read_only_fields = (
            'id',
            'phone_number',
            'role',
            'telegram_id',
            'is_active',
            'last_login_at',
        )

    def validate_email(self, value):
        value = value.lower().strip()
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Bu email allaqachon band.')
        return value


class RegisterSerializer(serializers.ModelSerializer):
    # Model validatori xom qiymatni tekshiradi; bu yerda avval normalizatsiya
    # qilamiz, shuning uchun maydon qayta e'lon qilinadi.
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = ('id', 'full_name', 'phone_number', 'email', 'password', 'bio', 'avatar')
        extra_kwargs = {
            'bio': {'required': False},
            'avatar': {'required': False},
        }

    def validate_phone_number(self, value):
        value = normalize_phone_number(value)
        if not re.match(r'^\+998\d{9}$', value):
            raise serializers.ValidationError(
                "Telefon raqami '+998901234567' formatida bo'lishi kerak."
            )
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Bu email allaqachon band.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        # is_active=False — akkaunt Telegram bot orqali tasdiqlanmaguncha yopiq turadi.
        user = User.objects.create_user(password=password, **validated_data)
        # Hozircha kod hech qayerga yuborilmaydi — admin paneldan ko'riladi.
        create_verification_code(user)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Plan bo'yicha 3 xil xato holati 3 xil javob qaytaradi:
    user yo'q -> 404, parol xato -> 400, is_active=False -> 403.
    Status kodlar `view` da `detail` ichidagi `code` orqali beriladi.
    """

    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        phone_number = normalize_phone_number(attrs.get('phone_number'))
        password = attrs.get('password')

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': 'Bunday foydalanuvchi topilmadi.', 'code': 'user_not_found'}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {'detail': 'Telefon raqam yoki parol xato.', 'code': 'invalid_credentials'}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {'detail': 'Akkaunt tasdiqlanmagan.', 'code': 'inactive_account'}
            )

        attrs['user'] = user
        return attrs
