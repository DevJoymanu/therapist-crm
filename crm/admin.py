from django.contrib import admin

from .models import Appointment, AppointmentRequest, ClientConsent, Patient, ScoreEntry, ScoringCriterion, SessionNote, ShareableLink


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


@admin.register(ClientConsent)
class ClientConsentAdmin(admin.ModelAdmin):
    list_display = ("patient", "is_signed", "client_signed_date", "counsellor_signed_date")
    list_filter = ("client_signed_date",)
    search_fields = ("patient__first_name", "patient__last_name", "client_name")
    readonly_fields = ("token",)
