import math

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, VerificationCode
from .serializers import (
    ConfirmSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendCodeSerializer,
    UserSerializer,
    get_tokens_for_user,
)
from .services import create_verification_code


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RegisterResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    detail = serializers.CharField()


class ResendCodeResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    expires_in = serializers.IntegerField(help_text='Kod necha soniya amal qiladi')


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


@extend_schema(
    summary="Ro'yxatdan o'tish",
    auth=[],
    responses={201: RegisterResponseSerializer},
)
class RegisterAPIView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — ro'yxatdan o'tish (is_active=False)."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'user': UserSerializer(user, context=self.get_serializer_context()).data,
                'detail': "Ro'yxatdan o'tdingiz. Akkauntni tasdiqlash uchun "
                          "Telegram botga /start bosing va raqamingizni yuboring.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """POST /api/v1/auth/login/ — {phone_number, password} → {access, refresh, user}."""

    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    # serializer'dagi `code` ga mos HTTP status kodlar
    ERROR_STATUSES = {
        'user_not_found': status.HTTP_404_NOT_FOUND,
        'invalid_credentials': status.HTTP_400_BAD_REQUEST,
        'inactive_account': status.HTTP_403_FORBIDDEN,
    }

    @extend_schema(
        summary='Login (JWT olish)',
        auth=[],
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(DetailSerializer, description='Telefon raqam yoki parol xato'),
            403: OpenApiResponse(DetailSerializer, description='Akkaunt tasdiqlanmagan'),
            404: OpenApiResponse(DetailSerializer, description='Bunday foydalanuvchi topilmadi'),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            detail = exc.detail
            code = detail.get('code') if isinstance(detail, dict) else None
            if code:
                code = str(code[0]) if isinstance(code, list) else str(code)
            if code in self.ERROR_STATUSES:
                message = detail.get('detail')
                message = str(message[0]) if isinstance(message, list) else str(message)
                return Response({'detail': message}, status=self.ERROR_STATUSES[code])
            raise

        user = serializer.validated_data['user']

        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])

        tokens = get_tokens_for_user(user)
        return Response(
            {**tokens, 'user': UserSerializer(user, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )


class ConfirmAPIView(APIView):
    """
    POST /api/v1/auth/confirm/ — {phone_number, code}.
    Kod to'g'ri bo'lsa user aktivlashtiriladi va JWT qaytariladi.
    Kod xato bo'lsa `attempts` bittaga oshadi.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ConfirmSerializer

    @extend_schema(
        summary='Tasdiqlash kodi orqali akkauntni aktivlashtirish',
        auth=[],
        request=ConfirmSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(
                DetailSerializer,
                description='Kod xato / muddati o\'tgan / urinishlar tugagan / akkaunt allaqachon tasdiqlangan',
            ),
            404: OpenApiResponse(DetailSerializer, description='Bunday foydalanuvchi topilmadi'),
        },
    )
    
    def post(self, request):
        serializer = ConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        entered_code = serializer.validated_data['code']

        user = User.objects.filter(phone_number=phone_number).first()
        if user is None:
            return self.error('Bunday foydalanuvchi topilmadi.', status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return self.error('Akkaunt allaqachon tasdiqlangan.')

        code = (
            user.codes
            .filter(purpose=VerificationCode.Purpose.REGISTER, is_used=False)
            .order_by('-created_at')
            .first()
        )
        if code is None:
            return self.error("Faol tasdiqlash kodi topilmadi. Yangi kod so'rang.")

        max_attempts = settings.VERIFICATION_CODE_MAX_ATTEMPTS
        if code.attempts >= max_attempts:
            return self.error("Urinishlar soni tugadi. Yangi kod so'rang.")

        if code.expires_at <= timezone.now():
            return self.error("Kodning muddati o'tgan. Yangi kod so'rang.")

        if code.code != entered_code:
            VerificationCode.objects.filter(pk=code.pk).update(attempts=F('attempts') + 1)
            remaining = max_attempts - code.attempts - 1
            if remaining <= 0:
                return self.error("Kod xato. Urinishlar soni tugadi, yangi kod so'rang.")
            return self.error(f'Kod xato. Qolgan urinishlar: {remaining}.')

        with transaction.atomic():
            code.is_used = True
            code.save(update_fields=['is_used'])

            user.is_active = True
            user.last_login_at = timezone.now()
            user.save(update_fields=['is_active', 'last_login_at'])

        tokens = get_tokens_for_user(user)
        return Response(
            {**tokens, 'user': UserSerializer(user, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def error(message, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': message}, status=status_code)


class ResendCodeAPIView(APIView):
    """
    POST /api/v1/auth/resend-code/ — {phone_number}.
    Userda ishlatilmagan va muddati o'tmagan kod bo'lsa yangi kod yaratilmaydi.
    Hozircha kod hech qayerga yuborilmaydi — admin paneldan ko'riladi.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ResendCodeSerializer

    @extend_schema(
        summary='Yangi tasdiqlash kodi olish',
        auth=[],
        request=ResendCodeSerializer,
        responses={
            201: ResendCodeResponseSerializer,
            400: OpenApiResponse(
                DetailSerializer,
                description='Avvalgi kod hali amal qiladi / akkaunt allaqachon tasdiqlangan',
            ),
            404: OpenApiResponse(DetailSerializer, description='Bunday foydalanuvchi topilmadi'),
        },
    )
    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        with transaction.atomic():
            # bir vaqtda kelgan so'rovlar ikkita kod yaratib yubormasligi uchun
            user = User.objects.select_for_update().filter(phone_number=phone_number).first()
            if user is None:
                return self.error('Bunday foydalanuvchi topilmadi.', status.HTTP_404_NOT_FOUND)

            if user.is_active:
                return self.error('Akkaunt allaqachon tasdiqlangan.')

            now = timezone.now()
            active_code = (
                user.codes
                .filter(
                    purpose=VerificationCode.Purpose.REGISTER,
                    is_used=False,
                    expires_at__gt=now,
                    # urinishlari tugagan kod bilan baribir tasdiqlab bo'lmaydi
                    attempts__lt=settings.VERIFICATION_CODE_MAX_ATTEMPTS,
                )
                .order_by('-expires_at')
                .first()
            )
            if active_code is not None:
                seconds = math.ceil((active_code.expires_at - now).total_seconds())
                return self.error(
                    f"Avvalgi kod hali amal qiladi. {seconds} soniyadan keyin urinib ko'ring."
                )

            code = create_verification_code(user)

        return Response(
            {
                'detail': 'Yangi tasdiqlash kodi yaratildi.',
                'expires_in': math.ceil((code.expires_at - timezone.now()).total_seconds()),
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def error(message, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': message}, status=status_code)


@extend_schema(summary='Joriy foydalanuvchi profili')
class MeAPIView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/v1/auth/me/ — faqat autentifikatsiyadan o'tgan user uchun."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user
