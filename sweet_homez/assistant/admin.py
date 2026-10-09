from django.contrib import admin

from .models import Inquiry, SearchConversation, SearchMessage, SearchRequirements, ViewingRequest


class SearchMessageInline(admin.TabularInline):
    model = SearchMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")


@admin.register(SearchConversation)
class SearchConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "language", "created_at", "updated_at")
    list_filter = ("language",)
    inlines = (SearchMessageInline,)


admin.site.register(SearchRequirements)
admin.site.register(Inquiry)
admin.site.register(ViewingRequest)
