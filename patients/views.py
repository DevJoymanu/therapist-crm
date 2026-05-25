from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.views import SendBookingLinkMixin, TherapistRequiredMixin
from notes.services import calculate_session_score, patient_score_trends, patient_table_rows

from .forms import PatientForm
from .models import ClientConsent, Patient
from .services import patient_queryset_for


class PatientListView(SendBookingLinkMixin, TherapistRequiredMixin, ListView):
    template_name = "crm/patients.html"
    context_object_name = "patients"
    paginate_by = 20

    def get_queryset(self):
        queryset = patient_queryset_for(self.request.user)
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(first_name__icontains=query) | queryset.filter(
                last_name__icontains=query
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient_rows"] = patient_table_rows(context["patients"])
        return context


class PatientDetailView(SendBookingLinkMixin, TherapistRequiredMixin, DetailView):
    template_name = "crm/patient_detail.html"
    context_object_name = "patient"

    def get_queryset(self):
        return patient_queryset_for(self.request.user).select_related("consent")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object
        context["appointments"] = patient.appointments.order_by("-starts_at")[:8]
        context["sessions"] = patient.session_notes.prefetch_related("scores__criterion")[:8]
        context["score_trends"] = patient_score_trends(patient)
        latest_session = context["sessions"][0] if context["sessions"] else None
        context["latest_algorithm"] = (
            calculate_session_score(latest_session) if latest_session else None
        )
        try:
            context["consent"] = patient.consent
        except Exception:
            context["consent"] = None
        return context


class PatientCreateView(TherapistRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = "crm/patient_form.html"

    def form_valid(self, form):
        form.instance.therapist = self.request.user
        response = super().form_valid(form)
        ClientConsent.objects.create(patient=self.object)
        return response


class PatientUpdateView(TherapistRequiredMixin, UpdateView):
    form_class = PatientForm
    template_name = "crm/patient_form.html"

    def get_queryset(self):
        return patient_queryset_for(self.request.user)


class PatientDeleteView(TherapistRequiredMixin, DeleteView):
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("patients:patient_list")

    def get_queryset(self):
        return patient_queryset_for(self.request.user)
