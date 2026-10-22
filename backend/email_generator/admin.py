from django.contrib import admin

from .models import GeneratedEmail


@admin.register(GeneratedEmail)
class GeneratedEmailAdmin(admin.ModelAdmin):
    list_display = ("subject", "user", "purpose", "tone", "language", "created_at")
    list_filter = ("tone", "language", "purpose", "created_at")
    search_fields = ("subject", "purpose", "body", "user__username")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user",)
    ordering = ("-created_at",)
