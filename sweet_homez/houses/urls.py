from rest_framework.routers import DefaultRouter

from .views import HouseMediaViewSet, HouseTranslationViewSet, HouseViewSet, NearbyFacilityViewSet

router = DefaultRouter()
router.register("houses", HouseViewSet, basename="house")
router.register("house-media", HouseMediaViewSet, basename="house-media")
router.register("house-translations", HouseTranslationViewSet, basename="house-translation")
router.register("nearby-facilities", NearbyFacilityViewSet, basename="nearby-facility")

urlpatterns = router.urls
