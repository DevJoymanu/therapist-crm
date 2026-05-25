from django import forms


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class TelInput(forms.TextInput):
    """Renders as <input type="tel"> — triggers mobile contact suggestions and the Contacts API."""
    input_type = "tel"


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
