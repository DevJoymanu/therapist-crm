from django.contrib import admin

from .models import ClientConsent, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "therapist", "email", "phone", "is_active")
    list_filter = ("is_active", "therapist")
    search_fields = ("first_name", "last_name", "email", "phone")


@admin.register(ClientConsent)
class ClientConsentAdmin(admin.ModelAdmin):
    list_display = ("patient", "is_signed", "client_signed_date", "counsellor_signed_date")
    list_filter = ("client_signed_date",)
    search_fields = ("patient__first_name", "patient__last_name", "client_name")
    readonly_fields = ("token",)
