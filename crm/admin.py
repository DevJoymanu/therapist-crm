from django.contrib import admin

from .models import Appointment, ClientConsent, Patient, ScoreEntry, ScoringCriterion, SessionNote


class ScoreEntryInline(admin.TabularInline):
    model = ScoreEntry
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "therapist", "email", "phone", "is_active")
    list_filter = ("is_active", "therapist")
    search_fields = ("first_name", "last_name", "email", "phone")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "starts_at", "ends_at", "status", "location")
    list_filter = ("status", "starts_at")
    search_fields = ("patient__first_name", "patient__last_name", "location")


@admin.register(SessionNote)
class SessionNoteAdmin(admin.ModelAdmin):
    list_display = ("patient", "session_date", "appointment")
    list_filter = ("session_date",)
    search_fields = ("patient__first_name", "patient__last_name", "presenting_concerns")
    inlines = [ScoreEntryInline]


@admin.register(ScoringCriterion)
class ScoringCriterionAdmin(admin.ModelAdmin):
    list_display = ("name", "therapist", "min_score", "max_score", "alert_threshold", "weight", "direction", "is_active")
    list_filter = ("direction", "is_active")


@admin.register(ScoreEntry)
class ScoreEntryAdmin(admin.ModelAdmin):
    list_display = ("session", "criterion", "value", "is_alert")
    list_filter = ("criterion",)


@admin.register(ClientConsent)
class ClientConsentAdmin(admin.ModelAdmin):
    list_display = ("patient", "is_signed", "client_signed_date", "counsellor_signed_date")
    list_filter = ("client_signed_date",)
    search_fields = ("patient__first_name", "patient__last_name", "client_name")
    readonly_fields = ("token",)
