from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from lookups.models import District, Locality, Region, Ward


class House(models.Model):
    class ListingType(models.TextChoices):
        RENT = "rent", _("For rent")
        SALE = "sale", _("For sale")

    class PricePeriod(models.TextChoices):
        ONE_TIME = "one_time", _("One-time sale price")
        DAILY = "daily", _("Per day")
        WEEKLY = "weekly", _("Per week")
        MONTHLY = "monthly", _("Per month")
        QUARTERLY = "quarterly", _("Per three months")
        SEMIANNUAL = "semiannual", _("Per six months")
        ANNUAL = "annual", _("Per year")

    class AgentFeeType(models.TextChoices):
        NONE = "none", _("No agent fee")
        FIXED = "fixed", _("Fixed amount")
        PERCENTAGE = "percentage", _("Percentage of price")

    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="house_listings")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    listing_type = models.CharField(max_length=10, choices=ListingType.choices)
    price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    price_period = models.CharField(max_length=20, choices=PricePeriod.choices, default=PricePeriod.ONE_TIME)
    advance_payment_months = models.PositiveSmallIntegerField(default=1)
    agent_fee_type = models.CharField(max_length=12, choices=AgentFeeType.choices, default=AgentFeeType.NONE)
    agent_fee_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    agent_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    address = models.CharField(max_length=255)
    ward = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Tanzania")
    region_record = models.ForeignKey(
        Region, on_delete=models.PROTECT, related_name="houses", null=True, blank=True
    )
    district_record = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name="houses", null=True, blank=True
    )
    ward_record = models.ForeignKey(
        Ward, on_delete=models.PROTECT, related_name="houses", null=True, blank=True
    )
    street = models.ForeignKey(
        Locality, on_delete=models.PROTECT, related_name="houses", null=True, blank=True
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    bedrooms = models.PositiveSmallIntegerField(default=1)
    ensuite_bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=1)
    kitchens = models.PositiveSmallIntegerField(default=1)
    parking_spaces = models.PositiveSmallIntegerField(default=0)

    electricity_available = models.BooleanField(default=False)
    water_available = models.BooleanField(default=False)
    security_available = models.BooleanField(default=False)
    furnished = models.BooleanField(default=False)
    has_garden = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)
    has_air_conditioning = models.BooleanField(default=False)
    has_internet = models.BooleanField(default=False)

    is_available = models.BooleanField(default=True)
    availability_last_confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing_type", "is_available"]),
            models.Index(fields=["region", "district"]),
            models.Index(fields=["bedrooms"]),
        ]

    @property
    def rooms(self):
        return self.bedrooms

    @property
    def location(self):
        return ", ".join(part for part in (self.address, self.ward, self.district, self.region, self.country) if part)

    def clean(self):
        errors = {}
        if self.district_record_id and self.region_record_id:
            if self.district_record.region_id != self.region_record_id:
                errors["district_record"] = "District must belong to the selected region."
        if self.ward_record_id and self.district_record_id:
            if self.ward_record.district_id != self.district_record_id:
                errors["ward_record"] = "Ward must belong to the selected district."
        if self.street_id and self.ward_record_id:
            if self.street.ward_id != self.ward_record_id:
                errors["street"] = "Street must belong to the selected ward."
        if self.ensuite_bedrooms > self.bedrooms:
            errors["ensuite_bedrooms"] = "Ensuite bedrooms cannot exceed total bedrooms."
        if self.listing_type == self.ListingType.SALE and self.price_period != self.PricePeriod.ONE_TIME:
            errors["price_period"] = "A property for sale must use the one-time price period."
        if self.listing_type == self.ListingType.RENT and self.price_period == self.PricePeriod.ONE_TIME:
            errors["price_period"] = "A rental must use a recurring price period."
        if self.agent_fee_type == self.AgentFeeType.FIXED and self.agent_fee_amount is None:
            errors["agent_fee_amount"] = "A fixed agent fee requires an amount."
        if self.agent_fee_type == self.AgentFeeType.PERCENTAGE and self.agent_fee_percentage is None:
            errors["agent_fee_percentage"] = "A percentage agent fee requires a percentage."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


class HouseTranslation(models.Model):
    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        SWAHILI = "sw", "Kiswahili"

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="translations")
    language_code = models.CharField(max_length=2, choices=Language.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)

    class Meta:
        ordering = ["language_code"]
        constraints = [
            models.UniqueConstraint(fields=["house", "language_code"], name="unique_house_language")
        ]

    def __str__(self):
        return f"{self.house_id}: {self.language_code}"


def house_media_upload_path(instance, filename):
    return f"houses/{instance.house_id}/{instance.media_type}/{filename}"


class HouseMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    file = models.FileField(upload_to=house_media_upload_path, blank=True)
    external_url = models.URLField(blank=True)
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name_plural = "house media"

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Provide either an uploaded file or an external URL.")


class NearbyFacility(models.Model):
    class FacilityType(models.TextChoices):
        ATM = "atm", "ATM"
        POLICE = "police", "Police station"
        GYM = "gym", "Gym"
        FUEL_STATION = "fuel_station", "Fuel station"
        PHARMACY = "pharmacy", "Pharmacy"
        HOSPITAL = "hospital", "Hospital or clinic"
        SCHOOL = "school", "School"
        MARKET = "market", "Market or supermarket"
        PUBLIC_TRANSPORT = "public_transport", "Public transport"
        RESTAURANT = "restaurant", "Restaurant"
        OTHER = "other", "Other"

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="nearby_facilities")
    facility_type = models.CharField(max_length=30, choices=FacilityType.choices)
    name = models.CharField(max_length=150, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["distance_km", "facility_type"]
