from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import District, Locality, LookupCategory, LookupValue, Region, Ward
from .serializers import DistrictSerializer, LocalitySerializer, LookupCategorySerializer, LookupValueSerializer, RegionSerializer, WardSerializer
from users.permissions import ModelActionPermissions, permission_required


@api_view(["POST"])
@permission_classes([permission_required("lookups.sync_administrative_areas")])
def sync_administrative_areas(request):
    backup = Path(settings.BASE_DIR) / "administrativeCorrectBackup.sql"
    if not backup.is_file():
        return Response({"detail": f"Administrative-area backup was not found at {backup}."}, status=404)
    call_command("sync_administrative_areas", str(backup), verbosity=0)
    return Response({
        "detail": "Administrative areas synchronized successfully.",
        "counts": {
            "regions": Region.objects.count(),
            "districts": District.objects.count(),
            "wards": Ward.objects.count(),
            "streets": Locality.objects.count(),
        },
    })


lookups_schema = extend_schema_view(
    list=extend_schema(tags=["Lookups"]),
    retrieve=extend_schema(tags=["Lookups"]),
)


class AdminWriteOrPublicRead(ModelActionPermissions):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or super().has_permission(request, view)


class AuthenticatedLookupViewSet(viewsets.ModelViewSet):
    # Read-only geographic data is available during onboarding. The global
    # API-key middleware still protects every /api/ request.
    permission_classes = [AdminWriteOrPublicRead]
    pagination_class = None


@lookups_schema
class LookupCategoryViewSet(AuthenticatedLookupViewSet):
    serializer_class = LookupCategorySerializer
    queryset = LookupCategory.objects.filter(is_active=True).prefetch_related("values")


@lookups_schema
class LookupValueViewSet(AuthenticatedLookupViewSet):
    serializer_class = LookupValueSerializer

    def get_queryset(self):
        queryset = LookupValue.objects.filter(is_active=True).select_related("category")
        category = self.request.query_params.get("category")
        return queryset.filter(category__code=category) if category else queryset


@lookups_schema
class RegionViewSet(AuthenticatedLookupViewSet):
    serializer_class = RegionSerializer
    def get_queryset(self):
        queryset = Region.objects.all()
        return queryset if self.request.user.has_perm("lookups.view_region") else queryset.filter(is_active=True)


@lookups_schema
class DistrictViewSet(AuthenticatedLookupViewSet):
    serializer_class = DistrictSerializer

    def get_queryset(self):
        queryset = District.objects.select_related("region")
        if not self.request.user.has_perm("lookups.view_district"): queryset = queryset.filter(is_active=True)
        region = self.request.query_params.get("region")
        return queryset.filter(region_id=region) if region and region.isdigit() else queryset


@lookups_schema
class WardViewSet(AuthenticatedLookupViewSet):
    serializer_class = WardSerializer

    def get_queryset(self):
        queryset = Ward.objects.select_related("district", "district__region")
        if not self.request.user.has_perm("lookups.view_ward"): queryset = queryset.filter(is_active=True)
        district = self.request.query_params.get("district")
        return queryset.filter(district_id=district) if district and district.isdigit() else queryset


@lookups_schema
class LocalityViewSet(AuthenticatedLookupViewSet):
    serializer_class = LocalitySerializer

    def get_queryset(self):
        queryset = Locality.objects.select_related(
            "ward", "ward__district", "ward__district__region", "locality_type"
        )
        if not self.request.user.has_perm("lookups.view_locality"): queryset = queryset.filter(is_active=True)
        ward = self.request.query_params.get("ward")
        locality_type = self.request.query_params.get("type")
        if ward and ward.isdigit():
            queryset = queryset.filter(ward_id=ward)
        if locality_type:
            queryset = queryset.filter(locality_type__code=locality_type)
        return queryset
