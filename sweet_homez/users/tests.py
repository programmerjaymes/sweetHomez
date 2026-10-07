from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Role, User


class AuthenticationApiTests(APITestCase):
    password = "StrongPass!234"

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
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile = self.client.get("/api/auth/me/")
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["email"], "jane@example.com")

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


class UserManagementApiTests(APITestCase):
    def setUp(self):
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
