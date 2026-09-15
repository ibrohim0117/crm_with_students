import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import VerificationCode


def generate_code():
    """6 xonali random kod (100000–999999)."""
    return str(secrets.randbelow(900000) + 100000)


def create_verification_code(user, purpose=VerificationCode.Purpose.REGISTER):
    """
    Userga yangi tasdiqlash kodi yaratadi.
    Shu maqsaddagi eski, ishlatilmagan kodlar bekor qilinadi.
    Hozircha kod hech qayerga yuborilmaydi — admin paneldan ko'riladi.
    """
    VerificationCode.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    return VerificationCode.objects.create(
        user=user,
        code=generate_code(),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=settings.VERIFICATION_CODE_TTL_SECONDS),
    )
