from collections import defaultdict

from django.db.models import Prefetch

from .models import ScoreEntry, ScoringCriterion, SessionNote

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


def session_queryset_for(therapist):
    return (
        SessionNote.objects.filter(patient__therapist=therapist)
        .select_related("patient", "appointment")
        .prefetch_related(
            Prefetch("scores", queryset=ScoreEntry.objects.select_related("criterion"))
        )
    )


def ensure_default_criteria(therapist):
    for data in DEFAULT_CRITERIA:
        ScoringCriterion.objects.get_or_create(
            therapist=therapist,
            name=data["name"],
            defaults=data,
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
        signals.append({
            "name": score.criterion.name,
            "raw": score.value,
            "wellness": round(wellness, 1),
            "weight": weight,
            "alert": score.is_alert,
        })

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


def patient_score_trends(patient):
    entries = (
        ScoreEntry.objects.filter(session__patient=patient)
        .select_related("criterion", "session")
        .order_by("session__session_date")
    )
    trends = defaultdict(list)
    for entry in entries:
        trends[entry.criterion.name].append({
            "date": entry.session.session_date.isoformat(),
            "value": entry.value,
            "alert": entry.is_alert,
        })
    return dict(trends)


def patient_table_rows(patients):
    return [
        {
            "patient": patient,
            "last_session": patient.session_notes.order_by("-session_date").first(),
            "risk": latest_risk_for(patient),
        }
        for patient in patients
    ]
