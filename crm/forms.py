from django import forms
from django.core.exceptions import ValidationError
from django.db.models import DurationField, ExpressionWrapper, F
from django.db.models.functions import Abs, Now
from datetime import timedelta

from .models import Appointment, Patient, ScoringCriterion, SessionNote


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


class PatientForm(StyledModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "emergency_contact",
            "medical_history",
            "notes",
            "is_active",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "medical_history": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


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
            .annotate(
                appointment_distance=Abs(
                    ExpressionWrapper(F("starts_at") - Now(), output_field=DurationField())
                )
            )
            .order_by("appointment_distance", "starts_at")
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

