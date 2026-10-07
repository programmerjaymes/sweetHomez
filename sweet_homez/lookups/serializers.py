from django.utils import translation
from rest_framework import serializers

from .models import District, Locality, LookupCategory, LookupValue, Region, Ward


class LocalizedModelSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj) -> str:
        request = self.context.get("request")
        language = getattr(request, "LANGUAGE_CODE", translation.get_language() or "en")
        return obj.name_sw or obj.name_en if language.startswith("sw") else obj.name_en


class LookupValueSerializer(LocalizedModelSerializer):
    category_code = serializers.CharField(source="category.code", read_only=True)

    class Meta:
        model = LookupValue
        fields = ["id", "category", "category_code", "code", "name", "name_en", "name_sw", "description_en", "description_sw", "sort_order", "is_active"]


class LookupCategorySerializer(LocalizedModelSerializer):
    values = LookupValueSerializer(many=True, read_only=True)

    class Meta:
        model = LookupCategory
        fields = ["id", "code", "name", "name_en", "name_sw", "description", "is_active", "values"]


class RegionSerializer(LocalizedModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "code", "country_code", "name", "name_en", "name_sw", "is_active"]


class DistrictSerializer(LocalizedModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = District
        fields = ["id", "region", "region_name", "code", "name", "name_en", "name_sw", "is_active"]


class WardSerializer(LocalizedModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = Ward
        fields = ["id", "district", "district_name", "code", "name", "name_en", "name_sw", "is_active"]


class LocalitySerializer(LocalizedModelSerializer):
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    locality_type_code = serializers.CharField(source="locality_type.code", read_only=True)

    class Meta:
        model = Locality
        fields = ["id", "ward", "ward_name", "locality_type", "locality_type_code", "code", "name", "name_en", "name_sw", "postal_code", "latitude", "longitude", "is_active"]
