from django.contrib.auth.models import Permission
from django.conf import settings
from django.core import signing
from django.test import override_settings
from unittest.mock import Mock, patch
from rest_framework import status
from rest_framework.test import APITestCase

from lookups.models import District, Region, Ward

from .models import AgentProfile, Role, Subscription, User


class AuthenticationApiTests(APITestCase):
    password = "StrongPass!234"

    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY=settings.API_KEY)

    def test_register_login_and_view_profile(self):
        response = self.client.post("/api/auth/register/", {
            "username": "jane", "email": "jane@example.com",
            "password": self.password, "password_confirm": self.password,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="jane")
        self.assertTrue(user.check_password(self.password))

        response = self.client.post("/api/auth/login/", {"username": "jane", "password": self.password})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.client.credentials(
            HTTP_X_API_KEY=settings.API_KEY,
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
        )
        profile = self.client.get("/api/auth/me/")
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["email"], "jane@example.com")

    def test_login_accepts_email_address(self):
        User.objects.create_user("email-user", "email-login@example.com", self.password)
        response = self.client.post("/api/auth/login/", {"username": "email-login@example.com", "password": self.password})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "email-login@example.com")

    def test_administrator_does_not_require_paid_onboarding(self):
        admin = User.objects.create_superuser("platform-admin", "platform-admin@example.com", self.password)
        admin.roles.add(Role.objects.create(name="Platform Administrator"))
        self.client.force_authenticate(admin)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["registration_complete"])
        self.assertTrue(response.data["is_staff"])
        self.assertTrue(response.data["is_superuser"])
        self.assertEqual(response.data["role_names"], ["Admin", "Platform Administrator"])

    def test_superuser_without_custom_role_is_reported_as_administrator(self):
        admin = User.objects.create_superuser("programmer", "programmer@example.com", self.password)
        self.client.force_authenticate(admin)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role_names"], ["Admin"])
        admin.refresh_from_db()
        role = admin.roles.get(name="Admin")
        self.assertEqual(role.permissions.count(), Permission.objects.count())

    @override_settings(DEBUG=True, TWILIO_ACCOUNT_SID="", TWILIO_AUTH_TOKEN="", TWILIO_FROM_NUMBER="")
    def test_phone_code_can_register_and_login_user_in_development(self):
        requested = self.client.post("/api/auth/phone/request/", {"phone_number": "+255712345678"})
        self.assertEqual(requested.status_code, status.HTTP_200_OK)
        verified = self.client.post("/api/auth/phone/verify/", {"phone_number": "+255712345678", "code": requested.data["debug_code"]})
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertEqual(verified.data["user"]["phone_number"], "+255712345678")
        self.assertTrue(verified.data["user"]["phone_verified"])

    @override_settings(GOOGLE_CLIENT_ID="client.apps.googleusercontent.com")
    @patch("users.views.jwt.decode")
    @patch("users.views.google_jwk_client.get_signing_key_from_jwt")
    def test_google_login_starts_paid_onboarding_for_a_new_user(self, signing_key, decode):
        signing_key.return_value = Mock(key="public-key")
        decode.return_value = {"sub": "google-123", "email": "google@example.com", "email_verified": True, "given_name": "Google", "family_name": "User"}
        response = self.client.post("/api/auth/google/", {"credential": "signed-token"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["requires_onboarding"])
        self.assertFalse(User.objects.filter(email="google@example.com").exists())
        completed = self.client.post("/api/auth/onboarding/complete/", {"onboarding_token": response.data["onboarding_token"], "plan_code": "home_basic", "phone_number": "+255712345678"})
        self.assertEqual(completed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(completed.data["user"]["email"], "google@example.com")
        self.assertEqual(User.objects.get(email="google@example.com").google_sub, "google-123")
        self.assertEqual(Subscription.objects.get(user__email="google@example.com").amount, 5000)

    @override_settings(GOOGLE_CLIENT_ID="client.apps.googleusercontent.com")
    @patch("users.views.jwt.decode")
    @patch("users.views.google_jwk_client.get_signing_key_from_jwt")
    def test_google_login_does_not_auto_register_unknown_user(self, signing_key, decode):
        signing_key.return_value = Mock(key="public-key")
        decode.return_value = {"sub": "new-google-user", "email": "new@example.com", "email_verified": True}
        response = self.client.post("/api/auth/google/", {"credential": "signed-token"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["requires_onboarding"])
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_onboarding_accepts_a_payment_number_used_by_another_account(self):
        payment_phone = "+255767716952"
        User.objects.create_user("phone-owner", "owner@example.com", self.password, phone_number=payment_phone)
        token = signing.dumps({
            "sub": "google-shared-payment-phone",
            "email": "new-agent@example.com",
            "first_name": "New",
            "last_name": "Agent",
            "picture": "",
            "existing_user_id": None,
        }, salt="google-onboarding")

        response = self.client.post("/api/auth/onboarding/complete/", {
            "onboarding_token": token,
            "plan_code": "agent_starter",
            "phone_number": payment_phone,
            "coverage_areas": "Dar es Salaam",
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        agent = User.objects.get(email="new-agent@example.com")
        self.assertIsNone(agent.phone_number)
        self.assertEqual(agent.subscription.payment_phone, payment_phone)
        self.assertEqual(agent.agent_profile.phone_number, payment_phone)

    def test_registration_cannot_assign_privileged_role(self):
        role = Role.objects.create(name="Administrators")
        response = self.client.post("/api/auth/register/", {
            "username": "normal", "email": "normal@example.com",
            "password": self.password, "password_confirm": self.password,
            "roles": [role.pk], "is_staff": True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="normal")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.roles.exists())

    def test_agent_registration_requires_and_saves_coverage(self):
        region = Region.objects.create(code="DSM", name_en="Dar es Salaam")
        district = District.objects.create(region=region, code="KIN", name_en="Kinondoni")
        ward = Ward.objects.create(district=district, code="MBZ", name_en="Mbezi Beach")
        response = self.client.post("/api/auth/register-agent/", {
            "username": "mbezi-agent",
            "email": "mbezi-agent@example.com",
            "password": self.password,
            "password_confirm": self.password,
            "agent_profile": {
                "agency_name": "Mbezi Homes",
                "phone_number": "+255700000002",
                "coverage_wards": [ward.pk],
            },
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = AgentProfile.objects.get(user__username="mbezi-agent")
        self.assertTrue(profile.coverage_wards.filter(pk=ward.pk).exists())
        self.assertTrue(profile.user.roles.filter(name="Agent").exists())

    def test_documentation_can_load_schema_before_api_key_authorization(self):
        self.client.credentials()
        docs = self.client.get("/docs/")
        public_schema = self.client.get("/schema/")
        protected_schema = self.client.get("/api/schema/")
        self.assertEqual(docs.status_code, status.HTTP_200_OK)
        self.assertEqual(public_schema.status_code, status.HTTP_200_OK)
        self.assertEqual(protected_schema.status_code, status.HTTP_401_UNAUTHORIZED)


class UserManagementApiTests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY=settings.API_KEY)
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "StrongPass!234")
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_role_with_permissions_and_assign_it(self):
        permission = Permission.objects.get(codename="view_user", content_type__app_label="users")
        role_response = self.client.post("/api/roles/", {"name": "Support", "permissions": [permission.pk]}, format="json")
        self.assertEqual(role_response.status_code, status.HTTP_201_CREATED)

        user_response = self.client.post("/api/users/", {
            "username": "support", "email": "support@example.com",
            "password": "StrongPass!234", "roles": [role_response.data["id"]],
        }, format="json")
        self.assertEqual(user_response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="support")
        self.assertTrue(user.check_password("StrongPass!234"))
        self.assertTrue(user.has_perm("users.view_user"))

    def test_delete_deactivates_instead_of_removing_user(self):
        user = User.objects.create_user("member", "member@example.com", "StrongPass!234")
        response = self.client.delete(f"/api/users/{user.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
