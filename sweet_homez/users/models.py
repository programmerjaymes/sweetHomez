from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Permission
from django.db import models

from lookups.models import District, Locality, Region, Ward


class Role(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Bundle(models.Model):
    class Audience(models.TextChoices):
        HOME_SEEKER = "home_seeker", "Normal user"
        AGENT = "agent", "Agent"

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    audience = models.CharField(max_length=20, choices=Audience.choices)
    description = models.TextField(blank=True)
    amount = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField(default=30)
    advantages = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    prompts_per_chat = models.PositiveIntegerField(null=True, blank=True)
    prompts_per_day = models.PositiveIntegerField(null=True, blank=True)
    prompts_per_week = models.PositiveIntegerField(null=True, blank=True)
    total_prompts = models.PositiveIntegerField(null=True, blank=True)
    max_houses = models.PositiveIntegerField(null=True, blank=True)
    video_upload_allowed = models.BooleanField(default=False)
    max_photos_per_house = models.PositiveIntegerField(default=12)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["audience", "display_order", "amount", "name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Application user with secure password handling and RBAC support."""

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    profile_image_url = models.URLField(blank=True)
    phone_verified = models.BooleanField(default=False)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    REQUIRED_FIELDS = ["email"]

    class Meta:
        permissions = [
            ("view_admin_dashboard", "Can view the administrator dashboard"),
            ("reset_user_password", "Can regenerate user passwords"),
        ]

    def __str__(self):
        return self.username


class PhoneVerificationCode(models.Model):
    phone_number = models.CharField(max_length=30, db_index=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AgentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agent_profile")
    agency_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=30)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    coverage_areas = models.TextField(blank=True, help_text="Comma-separated areas served by this agent")
    is_verified = models.BooleanField(default=False)
    coverage_regions = models.ManyToManyField(Region, blank=True, related_name="covering_agents")
    coverage_districts = models.ManyToManyField(District, blank=True, related_name="covering_agents")
    coverage_wards = models.ManyToManyField(Ward, blank=True, related_name="covering_agents")
    coverage_localities = models.ManyToManyField(Locality, blank=True, related_name="covering_agents")

    def __str__(self):
        return f"Agent profile: {self.user}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    account_type = models.CharField(max_length=20)
    plan_code = models.CharField(max_length=40)
    plan_name = models.CharField(max_length=100)
    amount = models.PositiveIntegerField()
    payment_phone = models.CharField(max_length=30)
    payment_reference = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    starts_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class LoginActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="login_activities")
    identifier = models.CharField(max_length=254, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "login activities"


class AuditTrail(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_actions")
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    target_label = models.CharField(max_length=254, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
