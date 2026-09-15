from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    ConfirmAPIView,
    LoginAPIView,
    MeAPIView,
    RegisterAPIView,
    ResendCodeAPIView,
)

app_name = 'users'

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('confirm/', ConfirmAPIView.as_view(), name='confirm'),
    path('resend-code/', ResendCodeAPIView.as_view(), name='resend_code'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('me/', MeAPIView.as_view(), name='me'),
]
