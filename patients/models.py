import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel


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
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    national_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="National ID / Passport No.",
        help_text="Government-issued ID or passport number. Used to prevent duplicate records.",
    )
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    marital_status = models.CharField(max_length=10, choices=MaritalStatus.choices, blank=True)
    religion = models.CharField(max_length=80, blank=True)
    occupation = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_relationship = models.CharField(max_length=80, blank=True)
    emergency_contact_phone1 = models.CharField(max_length=40, blank=True)
    emergency_contact_phone2 = models.CharField(max_length=40, blank=True)
    previous_treatment = models.TextField(blank=True)
    current_medication = models.TextField(blank=True)
    ok_to_leave_message = models.CharField(max_length=3, choices=YesNo.choices, blank=True)
    ok_to_contact_by_email = models.CharField(max_length=3, choices=YesNo.choices, blank=True)
    preferred_contact_method = models.CharField(max_length=5, choices=ContactMethod.choices, blank=True)
    referral_source = models.CharField(max_length=7, choices=ReferralSource.choices, blank=True)
    used_counselling_before = models.CharField(max_length=3, choices=YesNo.choices, blank=True)
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
        return reverse("patients:patient_detail", kwargs={"pk": self.pk})

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
        return reverse("booking:consent_form", kwargs={"token": self.token})

    def __str__(self):
        return f"Consent – {self.patient}"
