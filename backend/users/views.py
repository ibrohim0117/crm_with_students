from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    get_tokens_for_user,
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


class MeAPIView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/v1/auth/me/ — faqat autentifikatsiyadan o'tgan user uchun."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user
