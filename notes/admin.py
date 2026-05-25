from django.contrib import admin

from .models import ScoreEntry, ScoringCriterion, SessionNote


class ScoreEntryInline(admin.TabularInline):
    model = ScoreEntry
    extra = 0


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
