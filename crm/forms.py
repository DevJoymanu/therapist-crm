from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError

from .models import Appointment, AppointmentRequest, ClientConsent, Patient, ScoringCriterion, SessionNote


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class AppointmentSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        appointment = getattr(value, "instance", None)
        if appointment:
            option["attrs"]["data-patient-id"] = str(appointment.patient_id)
        return option


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = (
                "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
                "text-sm text-slate-900 outline-none transition placeholder:text-slate-400 "
                "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            )
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = (
                    "h-4 w-4 rounded border-slate-300 text-blue-600 "
                    "focus:ring-4 focus:ring-blue-100"
                )
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("data-searchable-select", "true")
                field.widget.attrs.setdefault("data-searchable-label", field.label.lower())
            field.widget.attrs.setdefault("class", css_class)


_SIMPLE_SELECT_FIELDS = [
    "gender",
    "marital_status",
    "ok_to_leave_message",
    "ok_to_contact_by_email",
    "preferred_contact_method",
    "referral_source",
    "used_counselling_before",
]


class PatientForm(StyledModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "national_id",
            "gender",
            "date_of_birth",
            "nationality",
            "marital_status",
            "religion",
            "occupation",
            "address",
            "phone",
            "email",
            "emergency_contact_name",
            "emergency_contact_relationship",
            "emergency_contact_phone1",
            "emergency_contact_phone2",
            "previous_treatment",
            "current_medication",
            "ok_to_leave_message",
            "ok_to_contact_by_email",
            "preferred_contact_method",
            "referral_source",
            "used_counselling_before",
            "notes",
            "is_active",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "address": forms.Textarea(attrs={"rows": 3}),
            "previous_treatment": forms.Textarea(attrs={"rows": 4}),
            "current_medication": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "emergency_contact_name": "Full name",
            "emergency_contact_relationship": "Relationship",
            "emergency_contact_phone1": "Contact number 1",
            "emergency_contact_phone2": "Contact number 2",
            "previous_treatment": "Previous treatment / counselling / therapy received",
            "current_medication": "Current medication (if any)",
            "ok_to_leave_message": "Is it OK to leave a message on the phone?",
            "ok_to_contact_by_email": "Can we contact by email?",
            "preferred_contact_method": "Best way to contact",
            "referral_source": "Who suggested this counselling?",
            "used_counselling_before": "Used counselling services before?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in _SIMPLE_SELECT_FIELDS:
            self.fields[name].widget.attrs.pop("data-searchable-select", None)
            self.fields[name].widget.attrs.pop("data-searchable-label", None)


class ClientConsentForm(forms.Form):
    client_name = forms.CharField(
        max_length=160,
        label="Full name (as signature)",
        widget=forms.TextInput(attrs={
            "class": (
                "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
                "text-sm text-slate-900 outline-none transition placeholder:text-slate-400 "
                "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            ),
            "placeholder": "Type your full name",
        }),
    )
    client_signed_date = forms.DateField(
        label="Date",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": (
                "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
                "text-sm text-slate-900 outline-none transition "
                "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            ),
        }),
    )
    agreed = forms.BooleanField(
        required=True,
        label="I have read and understood the terms outlined in this document.",
        widget=forms.CheckboxInput(attrs={
            "class": "h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-4 focus:ring-blue-100",
        }),
        error_messages={"required": "You must agree to the terms to continue."},
    )


class AppointmentForm(StyledModelForm):
    DURATION_CHOICES = [(minutes, f"{minutes} minutes") for minutes in range(15, 241, 15)]

    duration_minutes = forms.ChoiceField(
        label="Duration",
        choices=DURATION_CHOICES,
        initial=60,
    )

    class Meta:
        model = Appointment
        fields = [
            "patient",
            "starts_at",
            "status",
            "location",
            "reminder_email",
            "reminder_sms",
            "internal_notes",
        ]
        widgets = {
            "starts_at": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        therapist = kwargs.pop("therapist")
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(
            therapist=therapist,
            is_active=True,
        )
        if self.instance and self.instance.pk and self.instance.starts_at and self.instance.ends_at:
            duration = int((self.instance.ends_at - self.instance.starts_at).total_seconds() // 60)
            if duration % 15 == 0 and 15 <= duration <= 240:
                self.fields["duration_minutes"].initial = duration

        self.fields = {
            name: self.fields[name]
            for name in [
                "patient",
                "starts_at",
                "duration_minutes",
                "status",
                "location",
                "reminder_email",
                "reminder_sms",
                "internal_notes",
            ]
        }

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        duration_minutes = cleaned_data.get("duration_minutes")
        if starts_at and duration_minutes:
            cleaned_data["ends_at"] = starts_at + timedelta(minutes=int(duration_minutes))
        return cleaned_data

    def save(self, commit=True):
        appointment = super().save(commit=False)
        appointment.ends_at = self.cleaned_data["ends_at"]
        if commit:
            appointment.save()
            self.save_m2m()
        return appointment


class SessionNoteForm(StyledModelForm):
    class Meta:
        model = SessionNote
        fields = [
            "patient",
            "appointment",
            "session_date",
            "presenting_concerns",
            "interventions",
            "plan",
            "private_notes",
        ]
        widgets = {
            "appointment": AppointmentSelect(),
            "session_date": DateInput(),
            "presenting_concerns": forms.Textarea(attrs={"rows": 3}),
            "interventions": forms.Textarea(attrs={"rows": 3}),
            "plan": forms.Textarea(attrs={"rows": 3}),
            "private_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        therapist = kwargs.pop("therapist")
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(therapist=therapist)
        self.fields["appointment"].queryset = (
            Appointment.objects.filter(patient__therapist=therapist)
            .select_related("patient")
            .order_by("-starts_at")
        )

    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get("patient")
        appointment = cleaned_data.get("appointment")
        if patient and appointment and appointment.patient_id != patient.pk:
            self.add_error("appointment", "Choose an appointment for the selected patient.")
        return cleaned_data


class ScoringCriterionForm(StyledModelForm):
    class Meta:
        model = ScoringCriterion
        fields = [
            "name",
            "description",
            "min_score",
            "max_score",
            "alert_threshold",
            "weight",
            "direction",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_score = cleaned_data.get("min_score")
        max_score = cleaned_data.get("max_score")
        alert_threshold = cleaned_data.get("alert_threshold")
        if min_score is not None and max_score is not None and min_score >= max_score:
            raise ValidationError("Maximum score must be greater than minimum score.")
        if (
            alert_threshold is not None
            and min_score is not None
            and max_score is not None
            and not min_score <= alert_threshold <= max_score
        ):
            raise ValidationError("Alert threshold must sit inside the scoring range.")
        return cleaned_data


# ── Client-facing booking forms ───────────────────────────────────────────────

_B = (
    "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
    "text-sm text-slate-900 outline-none transition placeholder:text-slate-400 "
    "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)
_BS = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"


class NewClientBookingForm(forms.Form):
    first_name = forms.CharField(
        max_length=80,
        widget=forms.TextInput(attrs={"class": _B, "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=80,
        label="Surname",
        widget=forms.TextInput(attrs={"class": _B, "placeholder": "Surname"}),
    )
    phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": _B, "placeholder": "+263 77..."}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": _B, "placeholder": "email@example.com"}),
    )
    preferred_date = forms.DateField(
        label="Preferred date",
        widget=forms.DateInput(attrs={"type": "date", "class": _B}),
    )
    preferred_time_slot = forms.ChoiceField(
        label="Preferred time",
        choices=AppointmentRequest.PREFERRED_TIME_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": _BS}),
    )
    reason = forms.CharField(
        label="Reason for seeking counselling",
        required=False,
        widget=forms.Textarea(attrs={"class": _B, "rows": 3, "placeholder": "Brief description…"}),
    )


class ReturningClientBookingForm(forms.Form):
    client_id = forms.IntegerField(
        label="Client ID number",
        widget=forms.NumberInput(attrs={"class": _B, "placeholder": "e.g. 42"}),
        help_text="Your client ID is provided by your counsellor.",
    )
    last_name = forms.CharField(
        max_length=80,
        label="Surname (for verification)",
        widget=forms.TextInput(attrs={"class": _B, "placeholder": "Your surname"}),
    )
    preferred_date = forms.DateField(
        label="Preferred date",
        widget=forms.DateInput(attrs={"type": "date", "class": _B}),
    )
    preferred_time_slot = forms.ChoiceField(
        label="Preferred time",
        choices=AppointmentRequest.PREFERRED_TIME_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": _BS}),
    )
    reason = forms.CharField(
        label="Notes for your counsellor",
        required=False,
        widget=forms.Textarea(attrs={"class": _B, "rows": 3}),
    )


class PersonalizedBookingForm(forms.Form):
    preferred_date = forms.DateField(
        label="Preferred date",
        widget=forms.DateInput(attrs={"type": "date", "class": _B}),
    )
    preferred_time_slot = forms.ChoiceField(
        label="Preferred time",
        choices=AppointmentRequest.PREFERRED_TIME_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": _BS}),
    )
    reason = forms.CharField(
        label="Notes for your counsellor",
        required=False,
        widget=forms.Textarea(attrs={"class": _B, "rows": 3}),
    )


class ClientIntakeForm(StyledModelForm):
    """
    Public-facing form for clients to fill in their own WellMind intake details.
    Excludes therapist-only fields (notes, is_active) and identity fields
    (first_name, last_name) that the therapist already recorded.
    All searchable-select enhancements are disabled because this form is
    rendered on standalone pages that do not include that JavaScript.
    """

    class Meta:
        model = Patient
        fields = [
            "national_id",
            "gender", "date_of_birth", "nationality", "marital_status",
            "religion", "occupation", "address", "phone", "email",
            "emergency_contact_name", "emergency_contact_relationship",
            "emergency_contact_phone1", "emergency_contact_phone2",
            "previous_treatment", "current_medication",
            "ok_to_leave_message", "ok_to_contact_by_email",
            "preferred_contact_method", "referral_source",
            "used_counselling_before",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "address": forms.Textarea(attrs={"rows": 3}),
            "previous_treatment": forms.Textarea(attrs={"rows": 4}),
            "current_medication": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "national_id": "National ID / Passport No.",
            "emergency_contact_name": "Full name",
            "emergency_contact_relationship": "Relationship",
            "emergency_contact_phone1": "Contact number 1",
            "emergency_contact_phone2": "Contact number 2",
            "previous_treatment": "Previous treatment / counselling / therapy received",
            "current_medication": "Current medication (if any)",
            "ok_to_leave_message": "Is it OK to leave a message on the phone?",
            "ok_to_contact_by_email": "Can we contact by email?",
            "preferred_contact_method": "Best way to contact",
            "referral_source": "Who suggested this counselling?",
            "used_counselling_before": "Have you used counselling services before?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.pop("data-searchable-select", None)
            field.widget.attrs.pop("data-searchable-label", None)


class NewClientFullForm(StyledModelForm):
    """
    Used on the public booking portal when a Client ID is not found.
    Captures all WellMind intake fields plus first/last name so a full
    Patient record can be created on submission.
    Searchable-select is disabled because this form lives on a standalone page.
    """

    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "national_id",
            "gender", "date_of_birth", "nationality", "marital_status",
            "religion", "occupation", "address", "phone", "email",
            "emergency_contact_name", "emergency_contact_relationship",
            "emergency_contact_phone1", "emergency_contact_phone2",
            "previous_treatment", "current_medication",
            "ok_to_leave_message", "ok_to_contact_by_email",
            "preferred_contact_method", "referral_source",
            "used_counselling_before",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "address": forms.Textarea(attrs={"rows": 3}),
            "previous_treatment": forms.Textarea(attrs={"rows": 3}),
            "current_medication": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "first_name": "First Name",
            "last_name": "Surname",
            "national_id": "National ID / Passport No.",
            "emergency_contact_name": "Full name",
            "emergency_contact_relationship": "Relationship",
            "emergency_contact_phone1": "Contact number 1",
            "emergency_contact_phone2": "Contact number 2",
            "previous_treatment": "Previous counselling / therapy received",
            "current_medication": "Current medication (if any)",
            "ok_to_leave_message": "Is it OK to leave a message on your phone?",
            "ok_to_contact_by_email": "Can we contact you by email?",
            "preferred_contact_method": "Best way to contact you",
            "referral_source": "Who suggested this counselling?",
            "used_counselling_before": "Have you had counselling before?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.pop("data-searchable-select", None)
            field.widget.attrs.pop("data-searchable-label", None)


class ApproveRequestForm(forms.Form):
    starts_at = forms.DateTimeField(
        label="Appointment date & time",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": _B},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    duration_minutes = forms.ChoiceField(
        label="Duration",
        choices=[(45, "45 minutes"), (50, "50 minutes"), (60, "60 minutes"), (90, "90 minutes")],
        initial=50,
        widget=forms.Select(attrs={"class": _BS}),
    )
    location = forms.CharField(
        max_length=160,
        required=False,
        label="Location",
        widget=forms.TextInput(attrs={"class": _B, "placeholder": "Room 1, Online…"}),
    )
