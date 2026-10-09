from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AgentProfile, Role, User


class AgentProfileInline(admin.StackedInline):
    model = AgentProfile
    extra = 0
    filter_horizontal = ("coverage_regions", "coverage_districts", "coverage_wards", "coverage_localities")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    filter_horizontal = ("permissions",)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    filter_horizontal = (*UserAdmin.filter_horizontal, "roles")
    fieldsets = (*UserAdmin.fieldsets, ("Application roles", {"fields": ("roles",)}))
    inlines = (AgentProfileInline,)
