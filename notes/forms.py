from django import forms
from django.core.exceptions import ValidationError

from appointments.models import Appointment
from core.widgets import AppointmentSelect, DateInput, StyledModelForm
from patients.models import Patient

from .models import ScoringCriterion, SessionNote


class SessionNoteForm(StyledModelForm):
    class Meta:
        model = SessionNote
        fields = ["patient", "appointment", "session_date", "presenting_concerns",
                  "interventions", "plan", "private_notes"]
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
        fields = ["name", "description", "min_score", "max_score", "alert_threshold",
                  "weight", "direction", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

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
