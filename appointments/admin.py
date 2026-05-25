from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "starts_at", "ends_at", "status", "location")
    list_filter = ("status", "starts_at")
    search_fields = ("patient__first_name", "patient__last_name", "location")
