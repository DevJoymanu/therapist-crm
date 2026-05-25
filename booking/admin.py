from django.contrib import admin

from .models import AppointmentRequest, ShareableLink


@admin.register(ShareableLink)
class ShareableLinkAdmin(admin.ModelAdmin):
    list_display = ("patient", "link_type", "expires_at", "is_expired", "created_at")
    list_filter = ("link_type",)
    search_fields = ("patient__first_name", "patient__last_name")
    readonly_fields = ("token",)


@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ("client_full_name", "therapist", "preferred_date", "status", "is_new_client", "created_at")
    list_filter = ("status", "is_new_client", "preferred_date")
    search_fields = ("client_first_name", "client_last_name", "client_phone", "client_email")
    readonly_fields = ("token",)
