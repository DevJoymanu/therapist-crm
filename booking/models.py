import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel


class AppointmentRequest(TimeStampedModel):
    PREFERRED_TIME_CHOICES = [
        ("", "No preference"),
        ("morning", "Morning (8am–12pm)"),
        ("afternoon", "Afternoon (12pm–5pm)"),
        ("evening", "Evening (after 5pm)"),
    ]

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    therapist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointment_requests",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_requests",
    )
    client_first_name = models.CharField(max_length=80)
    client_last_name = models.CharField(max_length=80)
    client_phone = models.CharField(max_length=40, blank=True)
    client_email = models.EmailField(blank=True)
    preferred_date = models.DateField()
    preferred_time_slot = models.CharField(
        max_length=10, choices=PREFERRED_TIME_CHOICES, blank=True
    )
    reason = models.TextField(blank=True)
    is_new_client = models.BooleanField(default=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    therapist_response = models.TextField(blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    linked_appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_request",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client_full_name} – {self.preferred_date}"

    @property
    def client_full_name(self):
        return f"{self.client_first_name} {self.client_last_name}".strip()


class ShareableLink(TimeStampedModel):
    class LinkType(models.TextChoices):
        CONSENT = "consent", "Consent Form"
        BOOKING = "booking", "Appointment Booking"
        INTAKE = "intake", "Intake Form"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    link_type = models.CharField(max_length=10, choices=LinkType.choices)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="shareable_links",
    )
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_link_type_display()} for {self.patient} (expires {self.expires_at.date()})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def get_absolute_url(self):
        return reverse("booking:shared_link", kwargs={"token": self.token})
