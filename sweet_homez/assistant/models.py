import uuid

from django.conf import settings
from django.db import models

from houses.models import House


class SearchConversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="property_search_conversations",
        null=True,
        blank=True,
    )
    language = models.CharField(max_length=5, default="en")
    consecutive_off_topic_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class SearchMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        SearchConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class SearchRequirements(models.Model):
    conversation = models.OneToOneField(
        SearchConversation, on_delete=models.CASCADE, related_name="requirements"
    )
    listing_type = models.CharField(max_length=10, blank=True)
    location = models.CharField(max_length=150, blank=True)
    minimum_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    maximum_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_period = models.CharField(max_length=20, blank=True)
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    minimum_bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    minimum_parking_spaces = models.PositiveSmallIntegerField(null=True, blank=True)
    maximum_advance_months = models.PositiveSmallIntegerField(null=True, blank=True)
    water_required = models.BooleanField(null=True, blank=True)
    electricity_required = models.BooleanField(null=True, blank=True)
    security_required = models.BooleanField(null=True, blank=True)
    furnished_required = models.BooleanField(null=True, blank=True)
    internet_required = models.BooleanField(null=True, blank=True)
    nearby_facility = models.CharField(max_length=30, blank=True)
    maximum_facility_distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)


class Inquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CLOSED = "closed", "Closed"

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="inquiries")
    conversation = models.ForeignKey(
        SearchConversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="inquiries"
    )
    customer_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)


class ViewingRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="viewing_requests")
    conversation = models.ForeignKey(
        SearchConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viewing_requests",
    )
    customer_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30)
    preferred_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
