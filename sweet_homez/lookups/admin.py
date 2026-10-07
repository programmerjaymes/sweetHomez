from django.contrib import admin

from .models import District, Locality, LookupCategory, LookupValue, Region, Ward


class LookupValueInline(admin.TabularInline):
    model = LookupValue
    extra = 0


@admin.register(LookupCategory)
class LookupCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_sw", "is_active")
    search_fields = ("code", "name_en", "name_sw")
    inlines = (LookupValueInline,)


@admin.register(LookupValue)
class LookupValueAdmin(admin.ModelAdmin):
    list_display = ("category", "code", "name_en", "name_sw", "sort_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name_en", "name_sw")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_sw", "country_code", "is_active")
    search_fields = ("code", "name_en", "name_sw")


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_sw", "region", "is_active")
    list_filter = ("region",)
    search_fields = ("code", "name_en", "name_sw")


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_sw", "district", "is_active")
    list_filter = ("district__region", "district")
    search_fields = ("code", "name_en", "name_sw")


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_sw", "ward", "locality_type", "is_active")
    list_filter = ("locality_type", "ward__district__region")
    search_fields = ("code", "name_en", "name_sw")
