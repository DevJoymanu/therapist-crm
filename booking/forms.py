from django import forms

from .models import AppointmentRequest

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


class NewClientBookingForm(forms.Form):
    first_name = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"class": _B, "placeholder": "First name"}))
    last_name = forms.CharField(max_length=80, label="Surname", widget=forms.TextInput(attrs={"class": _B, "placeholder": "Surname"}))
    phone = forms.CharField(max_length=40, widget=forms.TextInput(attrs={"class": _B, "placeholder": "+263 77..."}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": _B, "placeholder": "email@example.com"}))
    preferred_date = forms.DateField(label="Preferred date", widget=forms.DateInput(attrs={"type": "date", "class": _B}))
    preferred_time_slot = forms.ChoiceField(
        label="Preferred time", choices=AppointmentRequest.PREFERRED_TIME_CHOICES,
        required=False, widget=forms.Select(attrs={"class": _BS}),
    )
    reason = forms.CharField(
        label="Reason for seeking counselling", required=False,
        widget=forms.Textarea(attrs={"class": _B, "rows": 3, "placeholder": "Brief description…"}),
    )


class ReturningClientBookingForm(forms.Form):
    client_id = forms.IntegerField(
        label="Client ID number",
        widget=forms.NumberInput(attrs={"class": _B, "placeholder": "e.g. 42"}),
        help_text="Your client ID is provided by your counsellor.",
    )
    last_name = forms.CharField(max_length=80, label="Surname (for verification)", widget=forms.TextInput(attrs={"class": _B, "placeholder": "Your surname"}))
    preferred_date = forms.DateField(label="Preferred date", widget=forms.DateInput(attrs={"type": "date", "class": _B}))
    preferred_time_slot = forms.ChoiceField(
        label="Preferred time", choices=AppointmentRequest.PREFERRED_TIME_CHOICES,
        required=False, widget=forms.Select(attrs={"class": _BS}),
    )
    reason = forms.CharField(label="Notes for your counsellor", required=False, widget=forms.Textarea(attrs={"class": _B, "rows": 3}))


class PersonalizedBookingForm(forms.Form):
    preferred_date = forms.DateField(label="Preferred date", widget=forms.DateInput(attrs={"type": "date", "class": _B}))
    preferred_time_slot = forms.ChoiceField(
        label="Preferred time", choices=AppointmentRequest.PREFERRED_TIME_CHOICES,
        required=False, widget=forms.Select(attrs={"class": _BS}),
    )
    reason = forms.CharField(label="Notes for your counsellor", required=False, widget=forms.Textarea(attrs={"class": _B, "rows": 3}))


class ApproveRequestForm(forms.Form):
    starts_at = forms.DateTimeField(
        label="Appointment date & time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": _B}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    duration_minutes = forms.ChoiceField(
        label="Duration",
        choices=[(45, "45 minutes"), (50, "50 minutes"), (60, "60 minutes"), (90, "90 minutes")],
        initial=50,
        widget=forms.Select(attrs={"class": _BS}),
    )
    location = forms.CharField(
        max_length=160, required=False, label="Location",
        widget=forms.TextInput(attrs={"class": _B, "placeholder": "Room 1, Online…"}),
    )
