from django import forms

from core.widgets import DateInput, StyledModelForm, TelInput, _SIMPLE_SELECT_FIELDS

from .models import Patient


class PatientForm(StyledModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "national_id", "gender", "date_of_birth",
            "nationality", "marital_status", "religion", "occupation", "address",
            "phone", "email", "emergency_contact_name", "emergency_contact_relationship",
            "emergency_contact_phone1", "emergency_contact_phone2", "previous_treatment",
            "current_medication", "ok_to_leave_message", "ok_to_contact_by_email",
            "preferred_contact_method", "referral_source", "used_counselling_before",
            "notes", "is_active",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "phone": TelInput(),
            "emergency_contact_phone1": TelInput(),
            "emergency_contact_phone2": TelInput(),
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


_INPUT_CSS = (
    "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 "
    "text-sm text-slate-900 outline-none transition placeholder:text-slate-400 "
    "focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)


class ClientConsentForm(forms.Form):
    client_name = forms.CharField(
        max_length=160,
        label="Full name (as signature)",
        widget=forms.TextInput(attrs={"class": _INPUT_CSS, "placeholder": "Type your full name"}),
    )
    client_signed_date = forms.DateField(
        label="Date",
        widget=forms.DateInput(attrs={"type": "date", "class": _INPUT_CSS}),
    )
    agreed = forms.BooleanField(
        required=True,
        label="I have read and understood the terms outlined in this document.",
        widget=forms.CheckboxInput(attrs={
            "class": "h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-4 focus:ring-blue-100",
        }),
        error_messages={"required": "You must agree to the terms to continue."},
    )


class ClientIntakeForm(StyledModelForm):
    class Meta:
        model = Patient
        fields = [
            "national_id", "gender", "date_of_birth", "nationality", "marital_status",
            "religion", "occupation", "address", "phone", "email",
            "emergency_contact_name", "emergency_contact_relationship",
            "emergency_contact_phone1", "emergency_contact_phone2",
            "previous_treatment", "current_medication", "ok_to_leave_message",
            "ok_to_contact_by_email", "preferred_contact_method", "referral_source",
            "used_counselling_before",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "phone": TelInput(),
            "emergency_contact_phone1": TelInput(),
            "emergency_contact_phone2": TelInput(),
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
    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "national_id", "gender", "date_of_birth",
            "nationality", "marital_status", "religion", "occupation", "address",
            "phone", "email", "emergency_contact_name", "emergency_contact_relationship",
            "emergency_contact_phone1", "emergency_contact_phone2", "previous_treatment",
            "current_medication", "ok_to_leave_message", "ok_to_contact_by_email",
            "preferred_contact_method", "referral_source", "used_counselling_before",
        ]
        widgets = {
            "date_of_birth": DateInput(),
            "phone": TelInput(),
            "emergency_contact_phone1": TelInput(),
            "emergency_contact_phone2": TelInput(),
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
