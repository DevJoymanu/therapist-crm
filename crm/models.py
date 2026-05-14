import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Patient(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class MaritalStatus(models.TextChoices):
        SINGLE = "single", "Single"
        MARRIED = "married", "Married"
        DIVORCED = "divorced", "Divorced"
        WIDOWED = "widowed", "Widowed"
        SEPARATED = "separated", "Separated"
        OTHER = "other", "Other"

    class ContactMethod(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    class ReferralSource(models.TextChoices):
        SELF = "self", "No one (Self Referral)"
        FRIEND = "friend", "Friend"
        FAMILY = "family", "Family Member"
        PARTNER = "partner", "Partner"

    class YesNo(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"

    therapist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patients",
    )
    # Client Information
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    marital_status = models.CharField(max_length=10, choices=MaritalStatus.choices, blank=True)
    religion = models.CharField(max_length=80, blank=True)
    occupation = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_relationship = models.CharField(max_length=80, blank=True)
    emergency_contact_phone1 = models.CharField(max_length=40, blank=True)
    emergency_contact_phone2 = models.CharField(max_length=40, blank=True)
    # Health & Medical
    previous_treatment = models.TextField(blank=True)
    current_medication = models.TextField(blank=True)
    # Communication
    ok_to_leave_message = models.CharField(max_length=3, choices=YesNo.choices, blank=True)
    ok_to_contact_by_email = models.CharField(max_length=3, choices=YesNo.choices, blank=True)
    preferred_contact_method = models.CharField(max_length=5, choices=ContactMethod.choices, blank=True)
    referral_source = models.CharField(max_length=7, choices=ReferralSource.choices, blank=True)
    used_counselling_before = models.CharField(max_length=3, choices=YesNo.choices, blank=True)
    # Internal
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    booking_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    intake_submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["therapist", "last_name"]),
            models.Index(fields=["therapist", "is_active"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self):
        return reverse("crm:patient_detail", kwargs={"pk": self.pk})

    @property
    def client_ref(self):
        return f"C-{self.pk:04d}"


class ClientConsent(TimeStampedModel):
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name="consent",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    client_name = models.CharField(max_length=160, blank=True)
    client_signed_date = models.DateField(null=True, blank=True)
    counsellor_signed_date = models.DateField(null=True, blank=True)

    @property
    def is_signed(self):
        return bool(self.client_name and self.client_signed_date)

    def get_form_url(self):
        return reverse("crm:consent_form", kwargs={"token": self.token})

    def __str__(self):
        return f"Consent – {self.patient}"


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    patient = models.ForeignKey(
        Patient,
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
        return reverse("crm:appointment_detail", kwargs={"pk": self.pk})


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
        Patient,
        on_delete=models.CASCADE,
        related_name="session_notes",
    )
    appointment = models.OneToOneField(
        Appointment,
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
        return reverse("crm:session_detail", kwargs={"pk": self.pk})


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
        Patient,
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
        Appointment,
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
        Patient,
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
        return reverse("crm:shared_link", kwargs={"token": self.token})
