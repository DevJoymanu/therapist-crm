import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    location = models.CharField(max_length=160, blank=True)
    reminder_email = models.BooleanField(default=False)
    reminder_sms = models.BooleanField(default=False)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["starts_at", "status"]),
            models.Index(fields=["patient", "starts_at"]),
        ]

    def __str__(self):
        return f"{self.patient} - {self.starts_at:%Y-%m-%d %H:%M}"

    @property
    def is_upcoming(self):
        return self.starts_at >= timezone.now() and self.status == self.Status.SCHEDULED

    def get_absolute_url(self):
        return reverse("appointments:appointment_detail", kwargs={"pk": self.pk})
