from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from .models import District, Locality, LookupCategory, LookupValue, Region, Ward
from .serializers import DistrictSerializer, LocalitySerializer, LookupCategorySerializer, LookupValueSerializer, RegionSerializer, WardSerializer


lookups_schema = extend_schema_view(
    list=extend_schema(tags=["Lookups"]),
    retrieve=extend_schema(tags=["Lookups"]),
)


class PublicLookupViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    pagination_class = None


@lookups_schema
class LookupCategoryViewSet(PublicLookupViewSet):
    serializer_class = LookupCategorySerializer
    queryset = LookupCategory.objects.filter(is_active=True).prefetch_related("values")


@lookups_schema
class LookupValueViewSet(PublicLookupViewSet):
    serializer_class = LookupValueSerializer

    def get_queryset(self):
        queryset = LookupValue.objects.filter(is_active=True).select_related("category")
        category = self.request.query_params.get("category")
        return queryset.filter(category__code=category) if category else queryset


@lookups_schema
class RegionViewSet(PublicLookupViewSet):
    serializer_class = RegionSerializer
    queryset = Region.objects.filter(is_active=True)


@lookups_schema
class DistrictViewSet(PublicLookupViewSet):
    serializer_class = DistrictSerializer

    def get_queryset(self):
        queryset = District.objects.filter(is_active=True).select_related("region")
        region = self.request.query_params.get("region")
        return queryset.filter(region_id=region) if region and region.isdigit() else queryset


@lookups_schema
class WardViewSet(PublicLookupViewSet):
    serializer_class = WardSerializer

    def get_queryset(self):
        queryset = Ward.objects.filter(is_active=True).select_related("district")
        district = self.request.query_params.get("district")
        return queryset.filter(district_id=district) if district and district.isdigit() else queryset


@lookups_schema
class LocalityViewSet(PublicLookupViewSet):
    serializer_class = LocalitySerializer

    def get_queryset(self):
        queryset = Locality.objects.filter(is_active=True).select_related("ward", "locality_type")
        ward = self.request.query_params.get("ward")
        locality_type = self.request.query_params.get("type")
        if ward and ward.isdigit():
            queryset = queryset.filter(ward_id=ward)
        if locality_type:
            queryset = queryset.filter(locality_type__code=locality_type)
        return queryset
