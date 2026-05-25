from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel


class ScoringCriterion(TimeStampedModel):
    class Direction(models.TextChoices):
        HIGHER_IS_BETTER = "higher_is_better", "Higher is better"
        LOWER_IS_BETTER = "lower_is_better", "Lower is better"

    therapist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scoring_criteria",
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    min_score = models.PositiveSmallIntegerField(default=0)
    max_score = models.PositiveSmallIntegerField(default=10)
    alert_threshold = models.PositiveSmallIntegerField(default=7)
    weight = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(10)],
        help_text="Relative importance used by the composite scoring algorithm.",
    )
    direction = models.CharField(
        max_length=30,
        choices=Direction.choices,
        default=Direction.HIGHER_IS_BETTER,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("therapist", "name")

    def __str__(self):
        return self.name


class SessionNote(TimeStampedModel):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="session_notes",
    )
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_note",
    )
    session_date = models.DateField(default=timezone.localdate)
    presenting_concerns = models.TextField(blank=True)
    interventions = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    private_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-session_date", "-created_at"]
        indexes = [
            models.Index(fields=["patient", "session_date"]),
        ]

    def __str__(self):
        return f"{self.patient} - {self.session_date:%Y-%m-%d}"

    def get_absolute_url(self):
        return reverse("notes:session_detail", kwargs={"pk": self.pk})


class ScoreEntry(TimeStampedModel):
    session = models.ForeignKey(
        SessionNote,
        on_delete=models.CASCADE,
        related_name="scores",
    )
    criterion = models.ForeignKey(
        ScoringCriterion,
        on_delete=models.PROTECT,
        related_name="score_entries",
    )
    value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["criterion__name"]
        unique_together = ("session", "criterion")
        indexes = [
            models.Index(fields=["criterion", "value"]),
        ]

    def __str__(self):
        return f"{self.criterion}: {self.value}"

    @property
    def is_alert(self):
        if self.criterion.direction == ScoringCriterion.Direction.LOWER_IS_BETTER:
            return self.value >= self.criterion.alert_threshold
        return self.value <= self.criterion.alert_threshold
