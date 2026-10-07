from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Permission
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Application user with secure password handling and RBAC support."""

    email = models.EmailField(unique=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username


class AgentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agent_profile")
    agency_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=30)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Agent profile: {self.user}"
