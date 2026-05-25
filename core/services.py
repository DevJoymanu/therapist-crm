from datetime import timedelta

from django.db.models import Avg, F, Prefetch
from django.utils import timezone

from appointments.models import Appointment
from appointments.services import appointment_queryset_for
from notes.models import ScoreEntry, ScoringCriterion, SessionNote
from notes.services import calculate_session_score, session_queryset_for
from patients.services import patient_queryset_for


def dashboard_context(therapist):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    appointments = appointment_queryset_for(therapist)
    sessions = session_queryset_for(therapist)
    recent_sessions = sessions[:6]
    high_risk_scores = (
        ScoreEntry.objects.filter(
            session__patient__therapist=therapist,
            criterion__direction=ScoringCriterion.Direction.LOWER_IS_BETTER,
            value__gte=F("criterion__alert_threshold"),
        )
        .select_related("session__patient", "criterion")
        .order_by("-session__session_date")[:8]
    )
    average_scores = list(
        ScoreEntry.objects.filter(session__patient__therapist=therapist)
        .values("criterion__name")
        .annotate(average=Avg("value"))
        .order_by("criterion__name")
    )
    return {
        "patient_count": patient_queryset_for(therapist).filter(is_active=True).count(),
        "sessions_this_week": sessions.filter(
            session_date__gte=week_start,
            session_date__lt=week_end,
        ).count(),
        "today_appointments": appointments.filter(starts_at__date=today).order_by("starts_at"),
        "upcoming_appointments": appointments.filter(
            starts_at__date__gte=today,
            status=Appointment.Status.SCHEDULED,
        ).order_by("starts_at")[:6],
        "recent_sessions": recent_sessions,
        "high_risk_scores": high_risk_scores,
        "average_scores": average_scores,
        "dashboard_chart": dashboard_score_chart(therapist),
    }


def dashboard_score_chart(therapist):
    from collections import defaultdict
    entries = (
        ScoreEntry.objects.filter(session__patient__therapist=therapist)
        .select_related("criterion", "session")
        .order_by("session__session_date")
    )
    labels = []
    series = defaultdict(dict)
    for entry in entries:
        label = entry.session.session_date.strftime("%b %d")
        if label not in labels:
            labels.append(label)
        series[entry.criterion.name][label] = entry.value
    return {
        "labels": labels,
        "datasets": [
            {"label": name, "data": [points.get(label) for label in labels]}
            for name, points in series.items()
        ],
    }


def notifications_for(therapist):
    now = timezone.now()
    today = timezone.localdate()
    items = []

    for appt in (
        Appointment.objects.filter(
            patient__therapist=therapist,
            starts_at__date=today,
            starts_at__gte=now,
            status=Appointment.Status.SCHEDULED,
        )
        .select_related("patient")
        .order_by("starts_at")[:5]
    ):
        items.append({
            "kind": "appointment",
            "label": appt.patient.full_name,
            "detail": f"Today at {appt.starts_at.strftime('%H:%M')}",
            "url": appt.get_absolute_url(),
        })

    for appt in (
        Appointment.objects.filter(
            patient__therapist=therapist,
            starts_at__lt=now,
            status=Appointment.Status.SCHEDULED,
        )
        .select_related("patient")
        .order_by("-starts_at")[:5]
    ):
        items.append({
            "kind": "noshow",
            "label": appt.patient.full_name,
            "detail": f"Missed {appt.starts_at.strftime('%b %d, %H:%M')}",
            "url": appt.get_absolute_url(),
        })

    seen = set()
    for entry in (
        ScoreEntry.objects.filter(
            session__patient__therapist=therapist,
            criterion__direction=ScoringCriterion.Direction.LOWER_IS_BETTER,
            value__gte=F("criterion__alert_threshold"),
        )
        .select_related("session__patient", "criterion")
        .order_by("-session__session_date")
    ):
        pid = entry.session.patient_id
        if pid in seen:
            continue
        seen.add(pid)
        items.append({
            "kind": "risk",
            "label": entry.session.patient.full_name,
            "detail": f"Alert: {entry.criterion.name}",
            "url": entry.session.patient.get_absolute_url(),
        })
        if len(seen) >= 5:
            break

    return items
