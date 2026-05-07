from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, F, Prefetch
from django.utils import timezone

from .models import Appointment, Patient, ScoreEntry, ScoringCriterion, SessionNote

RISK_LEVELS = {
    "low": {"label": "Low", "tone": "success"},
    "moderate": {"label": "Moderate", "tone": "warning"},
    "high": {"label": "High", "tone": "danger"},
    "unknown": {"label": "Unknown", "tone": "muted"},
}

DEFAULT_CRITERIA = [
    {
        "name": "Mood",
        "description": "Self-reported mood score.",
        "min_score": 0,
        "max_score": 10,
        "alert_threshold": 3,
        "weight": 1.0,
        "direction": ScoringCriterion.Direction.HIGHER_IS_BETTER,
    },
    {
        "name": "Progress",
        "description": "Clinical progress toward current treatment goals.",
        "min_score": 0,
        "max_score": 10,
        "alert_threshold": 3,
        "weight": 1.2,
        "direction": ScoringCriterion.Direction.HIGHER_IS_BETTER,
    },
    {
        "name": "Risk level",
        "description": "Clinical risk level for safety planning and review.",
        "min_score": 0,
        "max_score": 10,
        "alert_threshold": 7,
        "weight": 1.8,
        "direction": ScoringCriterion.Direction.LOWER_IS_BETTER,
    },
]


def ensure_default_criteria(therapist):
    for data in DEFAULT_CRITERIA:
        ScoringCriterion.objects.get_or_create(
            therapist=therapist,
            name=data["name"],
            defaults=data,
        )


def patient_queryset_for(therapist):
    return Patient.objects.filter(therapist=therapist)


def appointment_queryset_for(therapist):
    return Appointment.objects.filter(patient__therapist=therapist).select_related("patient")


def session_queryset_for(therapist):
    return (
        SessionNote.objects.filter(patient__therapist=therapist)
        .select_related("patient", "appointment")
        .prefetch_related(
            Prefetch("scores", queryset=ScoreEntry.objects.select_related("criterion"))
        )
    )


def criteria_for(therapist):
    ensure_default_criteria(therapist)
    return ScoringCriterion.objects.filter(therapist=therapist, is_active=True)


def save_scores_for_session(session, raw_scores):
    active_criteria = ScoringCriterion.objects.filter(
        therapist=session.patient.therapist,
        is_active=True,
    )
    for criterion in active_criteria:
        value = raw_scores.get(f"score_{criterion.pk}")
        if value in (None, ""):
            continue
        value = int(value)
        if value < criterion.min_score or value > criterion.max_score:
            continue
        ScoreEntry.objects.update_or_create(
            session=session,
            criterion=criterion,
            defaults={"value": value},
        )


def normalized_wellness(score):
    criterion = score.criterion
    score_range = criterion.max_score - criterion.min_score
    if score_range <= 0:
        return 0

    normalized = ((score.value - criterion.min_score) / score_range) * 100
    normalized = max(0, min(100, normalized))
    if criterion.direction == ScoringCriterion.Direction.LOWER_IS_BETTER:
        return 100 - normalized
    return normalized


def score_weight(score):
    return float(score.criterion.weight or 1)


def calculate_session_score(session):
    scores = list(session.scores.select_related("criterion"))
    if not scores:
        return {
            "wellness_score": None,
            "risk_score": None,
            "risk_level": RISK_LEVELS["unknown"],
            "trend": "No score data",
            "alerts": [],
            "signals": [],
        }

    weighted_total = 0
    weight_total = 0
    signals = []
    for score in scores:
        weight = score_weight(score)
        wellness = normalized_wellness(score)
        weighted_total += wellness * weight
        weight_total += weight
        signals.append(
            {
                "name": score.criterion.name,
                "raw": score.value,
                "wellness": round(wellness, 1),
                "weight": weight,
                "alert": score.is_alert,
            }
        )

    wellness_score = round(weighted_total / weight_total, 1) if weight_total else 0
    risk_score = round(100 - wellness_score, 1)
    if risk_score >= 65:
        risk_level = RISK_LEVELS["high"]
    elif risk_score >= 35:
        risk_level = RISK_LEVELS["moderate"]
    else:
        risk_level = RISK_LEVELS["low"]

    return {
        "wellness_score": wellness_score,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "trend": session_score_trend(session, wellness_score),
        "alerts": [score for score in scores if score.is_alert],
        "signals": signals,
    }


def session_score_trend(session, wellness_score):
    previous_session = (
        SessionNote.objects.filter(
            patient=session.patient,
            session_date__lt=session.session_date,
        )
        .prefetch_related(Prefetch("scores", queryset=ScoreEntry.objects.select_related("criterion")))
        .order_by("-session_date", "-created_at")
        .first()
    )
    if not previous_session or wellness_score is None:
        return "Baseline"

    previous_score = calculate_session_score(previous_session)["wellness_score"]
    if previous_score is None:
        return "Baseline"

    delta = round(wellness_score - previous_score, 1)
    if delta >= 5:
        return f"Improving +{delta}"
    if delta <= -5:
        return f"Declining {delta}"
    return f"Stable {delta:+}"


def session_score_summary(session):
    algorithm = calculate_session_score(session)
    return {
        "average": algorithm["wellness_score"],
        "risk_score": algorithm["risk_score"],
        "risk_level": algorithm["risk_level"],
        "trend": algorithm["trend"],
        "alerts": algorithm["alerts"],
        "signals": algorithm["signals"],
    }


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


def patient_score_trends(patient):
    entries = (
        ScoreEntry.objects.filter(session__patient=patient)
        .select_related("criterion", "session")
        .order_by("session__session_date")
    )
    trends = defaultdict(list)
    for entry in entries:
        trends[entry.criterion.name].append(
            {
                "date": entry.session.session_date.isoformat(),
                "value": entry.value,
                "alert": entry.is_alert,
            }
        )
    return dict(trends)


def dashboard_score_chart(therapist):
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
            {
                "label": name,
                "data": [points.get(label) for label in labels],
            }
            for name, points in series.items()
        ],
    }


def latest_risk_for(patient):
    session = (
        SessionNote.objects.filter(patient=patient)
        .prefetch_related(Prefetch("scores", queryset=ScoreEntry.objects.select_related("criterion")))
        .order_by("-session_date", "-created_at")
        .first()
    )
    if not session:
        return {"label": "Unknown", "tone": "muted", "value": None}
    algorithm = calculate_session_score(session)
    return {
        "label": algorithm["risk_level"]["label"],
        "tone": algorithm["risk_level"]["tone"],
        "value": algorithm["risk_score"],
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


def patient_table_rows(patients):
    rows = []
    for patient in patients:
        rows.append(
            {
                "patient": patient,
                "last_session": patient.session_notes.order_by("-session_date").first(),
                "risk": latest_risk_for(patient),
            }
        )
    return rows
