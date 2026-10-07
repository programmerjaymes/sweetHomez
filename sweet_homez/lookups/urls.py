from rest_framework.routers import DefaultRouter

from .views import DistrictViewSet, LocalityViewSet, LookupCategoryViewSet, LookupValueViewSet, RegionViewSet, WardViewSet

router = DefaultRouter()
router.register("lookup-categories", LookupCategoryViewSet, basename="lookup-category")
router.register("lookup-values", LookupValueViewSet, basename="lookup-value")
router.register("regions", RegionViewSet, basename="region")
router.register("districts", DistrictViewSet, basename="district")
router.register("wards", WardViewSet, basename="ward")
router.register("localities", LocalityViewSet, basename="locality")

urlpatterns = router.urls
