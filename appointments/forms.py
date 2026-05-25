from datetime import timedelta

from django import forms

from core.widgets import DateTimeInput, StyledModelForm
from patients.models import Patient

from .models import Appointment

_B = (
    "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
    "text-sm text-slate-900 outline-none transition placeholder:text-slate-400 "
    "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)
_BS = (
    "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
    "text-sm text-slate-900 outline-none transition "
    "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)


class AppointmentForm(StyledModelForm):
    DURATION_CHOICES = [(minutes, f"{minutes} minutes") for minutes in range(15, 241, 15)]

    duration_minutes = forms.ChoiceField(label="Duration", choices=DURATION_CHOICES, initial=60)

    class Meta:
        model = Appointment
        fields = ["patient", "starts_at", "status", "location", "reminder_email", "reminder_sms", "internal_notes"]
        widgets = {
            "starts_at": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        therapist = kwargs.pop("therapist")
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(therapist=therapist, is_active=True)
        if self.instance and self.instance.pk and self.instance.starts_at and self.instance.ends_at:
            duration = int((self.instance.ends_at - self.instance.starts_at).total_seconds() // 60)
            if duration % 15 == 0 and 15 <= duration <= 240:
                self.fields["duration_minutes"].initial = duration
        self.fields = {
            name: self.fields[name]
            for name in ["patient", "starts_at", "duration_minutes", "status", "location",
                         "reminder_email", "reminder_sms", "internal_notes"]
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
