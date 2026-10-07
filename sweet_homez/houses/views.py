from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import exceptions, viewsets

from .models import House, HouseMedia, HouseTranslation, NearbyFacility
from .permissions import IsAgentOwnerOrReadOnly
from .serializers import HouseMediaSerializer, HouseSerializer, HouseTranslationSerializer, NearbyFacilitySerializer


houses_schema = extend_schema_view(
    list=extend_schema(tags=["Houses"]),
    retrieve=extend_schema(tags=["Houses"]),
    create=extend_schema(tags=["Houses"]),
    update=extend_schema(tags=["Houses"]),
    partial_update=extend_schema(tags=["Houses"]),
    destroy=extend_schema(tags=["Houses"]),
)


@houses_schema
class HouseViewSet(viewsets.ModelViewSet):
    """Public browsing; Agent-role users manage their own listings."""

    serializer_class = HouseSerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = House.objects.select_related("agent", "agent__agent_profile").prefetch_related("media", "nearby_facilities", "translations")
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_available=True)
        elif not self.request.user.is_staff:
            queryset = queryset.filter(Q(is_available=True) | Q(agent=self.request.user))
        listing_type = self.request.query_params.get("listing_type")
        rooms = self.request.query_params.get("rooms") or self.request.query_params.get("bedrooms")
        region = self.request.query_params.get("region")
        if listing_type in House.ListingType.values:
            queryset = queryset.filter(listing_type=listing_type)
        if rooms and rooms.isdigit():
            queryset = queryset.filter(bedrooms=int(rooms))
        if region:
            queryset = queryset.filter(region__iexact=region)
        return queryset

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)


@houses_schema
class HouseMediaViewSet(viewsets.ModelViewSet):
    queryset = HouseMedia.objects.select_related("house", "house__agent")
    serializer_class = HouseMediaSerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(house__is_available=True)
        house_id = self.request.query_params.get("house")
        return queryset.filter(house_id=house_id) if house_id else queryset

    def perform_create(self, serializer):
        house = serializer.validated_data["house"]
        if not self.request.user.is_staff and house.agent_id != self.request.user.id:
            raise exceptions.PermissionDenied("You can add media only to your own listings.")
        serializer.save()


@houses_schema
class HouseTranslationViewSet(viewsets.ModelViewSet):
    queryset = HouseTranslation.objects.select_related("house", "house__agent")
    serializer_class = HouseTranslationSerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(house__is_available=True)
        house_id = self.request.query_params.get("house")
        return queryset.filter(house_id=house_id) if house_id else queryset

    def perform_create(self, serializer):
        house = serializer.validated_data["house"]
        if not self.request.user.is_staff and house.agent_id != self.request.user.id:
            raise exceptions.PermissionDenied("You can translate only your own listings.")
        serializer.save()


@houses_schema
class NearbyFacilityViewSet(viewsets.ModelViewSet):
    queryset = NearbyFacility.objects.select_related("house", "house__agent")
    serializer_class = NearbyFacilitySerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(house__is_available=True)
        house_id = self.request.query_params.get("house")
        return queryset.filter(house_id=house_id) if house_id else queryset

    def perform_create(self, serializer):
        house = serializer.validated_data["house"]
        if not self.request.user.is_staff and house.agent_id != self.request.user.id:
            raise exceptions.PermissionDenied("You can add facilities only to your own listings.")
        serializer.save()
