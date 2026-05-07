from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Patient, ScoreEntry, SessionNote
from .models import ScoringCriterion
from .services import (
    calculate_session_score,
    criteria_for,
    normalized_wellness,
    patient_queryset_for,
    save_scores_for_session,
)


class ScoringServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.therapist = User.objects.create_user(
            username="therapist",
            password="pass12345",
        )
        self.other_therapist = User.objects.create_user(
            username="other",
            password="pass12345",
        )
        self.patient = Patient.objects.create(
            therapist=self.therapist,
            first_name="Maya",
            last_name="Singh",
        )
        Patient.objects.create(
            therapist=self.other_therapist,
            first_name="Hidden",
            last_name="Patient",
        )
        self.session = SessionNote.objects.create(
            patient=self.patient,
            session_date=timezone.localdate(),
        )

    def test_default_criteria_and_scores_are_created(self):
        criteria = list(criteria_for(self.therapist))
        raw_scores = {f"score_{criterion.pk}": "5" for criterion in criteria}

        save_scores_for_session(self.session, raw_scores)

        self.assertEqual(ScoreEntry.objects.filter(session=self.session).count(), 3)

    def test_out_of_range_scores_are_ignored(self):
        criterion = criteria_for(self.therapist).first()

        save_scores_for_session(self.session, {f"score_{criterion.pk}": "99"})

        self.assertFalse(ScoreEntry.objects.filter(session=self.session).exists())

    def test_patient_queryset_is_scoped_to_therapist(self):
        patients = patient_queryset_for(self.therapist)

        self.assertEqual(list(patients), [self.patient])

    def test_lower_is_better_scores_are_inverted_for_wellness(self):
        criterion = ScoringCriterion.objects.create(
            therapist=self.therapist,
            name="Risk",
            min_score=0,
            max_score=10,
            alert_threshold=7,
            direction=ScoringCriterion.Direction.LOWER_IS_BETTER,
            weight=2,
        )
        score = ScoreEntry.objects.create(
            session=self.session,
            criterion=criterion,
            value=8,
        )

        self.assertEqual(normalized_wellness(score), 20)

    def test_composite_algorithm_uses_weights_and_classifies_risk(self):
        mood = ScoringCriterion.objects.create(
            therapist=self.therapist,
            name="Mood",
            min_score=0,
            max_score=10,
            alert_threshold=3,
            direction=ScoringCriterion.Direction.HIGHER_IS_BETTER,
            weight=1,
        )
        risk = ScoringCriterion.objects.create(
            therapist=self.therapist,
            name="Risk",
            min_score=0,
            max_score=10,
            alert_threshold=7,
            direction=ScoringCriterion.Direction.LOWER_IS_BETTER,
            weight=3,
        )
        ScoreEntry.objects.create(session=self.session, criterion=mood, value=8)
        ScoreEntry.objects.create(session=self.session, criterion=risk, value=9)

        result = calculate_session_score(self.session)

        self.assertEqual(result["wellness_score"], 27.5)
        self.assertEqual(result["risk_score"], 72.5)
        self.assertEqual(result["risk_level"]["label"], "High")
