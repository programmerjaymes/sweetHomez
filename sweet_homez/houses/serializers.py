from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import translation
from rest_framework import serializers

from users.models import AgentProfile, User

from .models import House, HouseMedia, HouseTranslation, NearbyFacility


class AgentInfoSerializer(serializers.ModelSerializer):
    agency_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()
    license_number = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "agency_name", "phone_number", "whatsapp_number", "license_number", "is_verified"]

    def _profile_value(self, obj, field, default=""):
        try:
            return getattr(obj.agent_profile, field)
        except AgentProfile.DoesNotExist:
            return default

    def get_agency_name(self, obj) -> str:
        return self._profile_value(obj, "agency_name")

    def get_phone_number(self, obj) -> str:
        return self._profile_value(obj, "phone_number")

    def get_whatsapp_number(self, obj) -> str:
        return self._profile_value(obj, "whatsapp_number")

    def get_license_number(self, obj) -> str:
        return self._profile_value(obj, "license_number")

    def get_is_verified(self, obj) -> bool:
        return self._profile_value(obj, "is_verified", False)


class HouseMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = HouseMedia
        fields = ["id", "house", "media_type", "file", "file_url", "external_url", "caption", "is_primary", "display_order", "created_at"]
        read_only_fields = ["id", "file_url", "created_at"]

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def validate(self, attrs):
        if not attrs.get("file") and not attrs.get("external_url") and not getattr(self.instance, "file", None):
            raise serializers.ValidationError("Provide either a file or an external URL.")
        return attrs


class NearbyFacilitySerializer(serializers.ModelSerializer):
    facility_type_display = serializers.CharField(source="get_facility_type_display", read_only=True)

    class Meta:
        model = NearbyFacility
        fields = ["id", "house", "facility_type", "facility_type_display", "name", "distance_km"]
        read_only_fields = ["id"]


class HouseTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseTranslation
        fields = ["id", "house", "language_code", "title", "description", "address"]
        read_only_fields = ["id"]


class HouseSerializer(serializers.ModelSerializer):
    agent = AgentInfoSerializer(read_only=True)
    listing_type_display = serializers.CharField(source="get_listing_type_display", read_only=True)
    price_period_display = serializers.CharField(source="get_price_period_display", read_only=True)
    agent_fee_type_display = serializers.CharField(source="get_agent_fee_type_display", read_only=True)
    location = serializers.CharField(read_only=True)
    rooms = serializers.IntegerField(source="bedrooms", read_only=True)
    media = HouseMediaSerializer(many=True, read_only=True)
    nearby_facilities = NearbyFacilitySerializer(many=True, read_only=True)
    translations = HouseTranslationSerializer(many=True, read_only=True)
    language = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

    class Meta:
        model = House
        fields = [
            "id", "agent", "language", "available_languages", "title", "description", "listing_type", "listing_type_display",
            "price", "price_period", "price_period_display", "advance_payment_months",
            "agent_fee_type", "agent_fee_type_display", "agent_fee_amount", "agent_fee_percentage",
            "location", "address", "ward", "district", "region", "country", "latitude", "longitude",
            "region_record", "district_record", "ward_record", "street",
            "rooms", "bedrooms", "ensuite_bedrooms", "bathrooms", "kitchens", "parking_spaces",
            "electricity_available", "water_available", "security_available", "furnished", "has_garden",
            "has_balcony", "has_air_conditioning", "has_internet", "media", "nearby_facilities", "translations",
            "is_available", "availability_last_confirmed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "agent", "created_at", "updated_at"]

    def get_language(self, obj) -> str:
        request = self.context.get("request")
        return getattr(request, "LANGUAGE_CODE", translation.get_language() or "en").split("-")[0]

    def get_available_languages(self, obj) -> list[str]:
        return [item.language_code for item in obj.translations.all()]

    def to_representation(self, instance):
        language = self.get_language(instance)
        with translation.override(language):
            data = super().to_representation(instance)
        selected = next((item for item in instance.translations.all() if item.language_code == language), None)
        if selected is None:
            selected = next((item for item in instance.translations.all() if item.language_code == "en"), None)
        if selected:
            data.update(title=selected.title, description=selected.description, address=selected.address)
            location_parts = [selected.address, instance.ward, instance.district, instance.region, instance.country]
            data["location"] = ", ".join(part for part in location_parts if part)
            data["language"] = selected.language_code
        return data

    def validate(self, attrs):
        instance = self.instance or House()
        for field, value in attrs.items():
            setattr(instance, field, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs
