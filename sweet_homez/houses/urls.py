from rest_framework.routers import DefaultRouter

from django.urls import path
from .views import AgentListingDraftView, HouseMediaViewSet, HouseTranslationViewSet, HouseViewSet, NearbyFacilityViewSet

router = DefaultRouter()
router.register("houses", HouseViewSet, basename="house")
router.register("house-media", HouseMediaViewSet, basename="house-media")
router.register("house-translations", HouseTranslationViewSet, basename="house-translation")
router.register("nearby-facilities", NearbyFacilityViewSet, basename="nearby-facility")

urlpatterns = [path("agent/listing-draft/", AgentListingDraftView.as_view(), name="agent-listing-draft"), *router.urls]
