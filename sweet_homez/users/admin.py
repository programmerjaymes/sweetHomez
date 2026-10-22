from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AgentProfile, Bundle, Role, User


class AgentProfileInline(admin.StackedInline):
    model = AgentProfile
    extra = 0
    filter_horizontal = ("coverage_regions", "coverage_districts", "coverage_wards", "coverage_localities")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    filter_horizontal = ("permissions",)


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "audience", "amount", "duration_days", "is_default", "is_active", "display_order")
    list_filter = ("audience", "is_default", "is_active")
    search_fields = ("name", "code", "description")
    ordering = ("audience", "display_order", "amount")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    filter_horizontal = (*UserAdmin.filter_horizontal, "roles")
    fieldsets = (*UserAdmin.fieldsets, ("Application roles", {"fields": ("roles",)}))
    inlines = (AgentProfileInline,)
