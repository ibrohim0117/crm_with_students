from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, VerificationCode


class RegisterAPITests(APITestCase):
    url = reverse('users:register')

    def test_register_creates_inactive_user_with_hashed_password(self):
        payload = {
            'full_name': 'Ali Valiyev',
            'phone_number': '+998901234567',
            'email': 'Ali@Example.com',
            'password': 'StrongPass123',
        }
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(phone_number='+998901234567')
        self.assertFalse(user.is_active)
        self.assertEqual(user.email, 'ali@example.com')
        self.assertNotEqual(user.password, 'StrongPass123')
        self.assertTrue(user.check_password('StrongPass123'))
        self.assertNotIn('password', response.data['user'])

    def test_phone_number_is_normalized(self):
        response = self.client.post(self.url, {
            'full_name': 'Ali Valiyev',
            'phone_number': '90 123 45 67',
            'email': 'ali@example.com',
            'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(phone_number='+998901234567').exists())

    def test_duplicate_phone_and_email_rejected(self):
        User.objects.create_user('+998901234567', 'ali@example.com', 'Ali', 'StrongPass123')

        response = self.client.post(self.url, {
            'full_name': 'Vali',
            'phone_number': '+998901234567',
            'email': 'vali@example.com',
            'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

        response = self.client.post(self.url, {
            'full_name': 'Vali',
            'phone_number': '+998901112233',
            'email': 'ALI@example.com',
            'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class LoginAPITests(APITestCase):
    url = reverse('users:login')

    def setUp(self):
        self.user = User.objects.create_user(
            '+998901234567', 'ali@example.com', 'Ali Valiyev', 'StrongPass123'
        )

    def test_unknown_user_returns_404(self):
        response = self.client.post(self.url, {
            'phone_number': '+998900000000', 'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_password_returns_400(self):
        response = self.client.post(self.url, {
            'phone_number': '+998901234567', 'password': 'WrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_account_returns_403(self):
        response = self.client.post(self.url, {
            'phone_number': '+998901234567', 'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_active_user_gets_tokens(self):
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])

        response = self.client.post(self.url, {
            'phone_number': '901234567', 'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['phone_number'], '+998901234567')

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login_at)

    def test_refresh_endpoint_returns_new_access(self):
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])
        refresh = self.client.post(self.url, {
            'phone_number': '+998901234567', 'password': 'StrongPass123',
        }).data['refresh']

        response = self.client.post(reverse('users:token_refresh'), {'refresh': refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class MeAPITests(APITestCase):
    url = reverse('users:me')

    def setUp(self):
        self.user = User.objects.create_user(
            '+998901234567', 'ali@example.com', 'Ali Valiyev', 'StrongPass123', is_active=True
        )

    def authenticate(self):
        access = self.client.post(reverse('users:login'), {
            'phone_number': '+998901234567', 'password': 'StrongPass123',
        }).data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_anonymous_request_is_rejected(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_reads_own_profile(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '+998901234567')
        self.assertEqual(response.data['role'], User.Role.USER)

    def test_patch_updates_editable_fields_only(self):
        self.authenticate()
        response = self.client.patch(self.url, {
            'full_name': 'Ali Valiyevich',
            'bio': 'CRM foydalanuvchisi',
            'phone_number': '+998900000000',
            'role': User.Role.ADMIN,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'Ali Valiyevich')
        self.assertEqual(self.user.bio, 'CRM foydalanuvchisi')
        self.assertEqual(self.user.phone_number, '+998901234567')
        self.assertEqual(self.user.role, User.Role.USER)

    def test_patch_rejects_email_taken_by_another_user(self):
        User.objects.create_user('+998901112233', 'vali@example.com', 'Vali', 'StrongPass123')
        self.authenticate()
        response = self.client.patch(self.url, {'email': 'vali@example.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_is_not_allowed(self):
        self.authenticate()
        response = self.client.put(self.url, {'full_name': 'X'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class RegisterVerificationCodeTests(APITestCase):
    def test_register_creates_verification_code(self):
        response = self.client.post(reverse('users:register'), {
            'full_name': 'Ali Valiyev',
            'phone_number': '+998901234567',
            'email': 'ali@example.com',
            'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(phone_number='+998901234567')
        code = user.codes.get()
        self.assertEqual(code.purpose, VerificationCode.Purpose.REGISTER)
        self.assertRegex(code.code, r'^\d{6}$')
        self.assertTrue(code.is_valid())
        # kod javobda qaytmasligi kerak
        self.assertNotIn(code.code, response.content.decode())
