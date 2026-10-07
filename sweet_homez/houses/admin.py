from django.contrib import admin

from .models import House, HouseMedia, HouseTranslation, NearbyFacility


class HouseMediaInline(admin.TabularInline):
    model = HouseMedia
    extra = 0


class NearbyFacilityInline(admin.TabularInline):
    model = NearbyFacility
    extra = 0


class HouseTranslationInline(admin.TabularInline):
    model = HouseTranslation
    extra = 0


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ("title", "agent", "listing_type", "bedrooms", "price", "region", "is_available")
    list_filter = ("listing_type", "bedrooms", "region", "is_available")
    search_fields = ("title", "description", "address", "ward", "district", "region")
    inlines = (HouseTranslationInline, HouseMediaInline, NearbyFacilityInline)


@admin.register(HouseMedia)
class HouseMediaAdmin(admin.ModelAdmin):
    list_display = ("house", "media_type", "caption", "is_primary", "display_order")


@admin.register(NearbyFacility)
class NearbyFacilityAdmin(admin.ModelAdmin):
    list_display = ("house", "facility_type", "name", "distance_km")
    list_filter = ("facility_type",)
