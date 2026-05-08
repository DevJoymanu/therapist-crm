from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import AppointmentForm, PatientForm, ScoringCriterionForm, SessionNoteForm
from .models import Appointment, Patient, ScoringCriterion, SessionNote
from .services import (
    criteria_for,
    calculate_session_score,
    dashboard_context,
    patient_queryset_for,
    patient_score_trends,
    patient_table_rows,
    save_scores_for_session,
    session_queryset_for,
    session_score_summary,
)


class TherapistRequiredMixin(LoginRequiredMixin):
    login_url = "login"


class DashboardView(TherapistRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(dashboard_context(self.request.user))
        return context


class PatientListView(TherapistRequiredMixin, ListView):
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


class PatientDetailView(TherapistRequiredMixin, DetailView):
    template_name = "crm/patient_detail.html"
    context_object_name = "patient"

    def get_queryset(self):
        return patient_queryset_for(self.request.user)

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
        return context


class PatientCreateView(TherapistRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = "crm/form.html"

    def form_valid(self, form):
        form.instance.therapist = self.request.user
        return super().form_valid(form)


class PatientUpdateView(TherapistRequiredMixin, UpdateView):
    form_class = PatientForm
    template_name = "crm/form.html"

    def get_queryset(self):
        return patient_queryset_for(self.request.user)


class PatientDeleteView(TherapistRequiredMixin, DeleteView):
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:patient_list")

    def get_queryset(self):
        return patient_queryset_for(self.request.user)


class AppointmentListView(TherapistRequiredMixin, ListView):
    template_name = "crm/appointment_list.html"
    context_object_name = "appointments"

    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user).select_related(
            "patient"
        )


class AppointmentDetailView(TherapistRequiredMixin, DetailView):
    template_name = "crm/appointment_detail.html"
    context_object_name = "appointment"

    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user).select_related(
            "patient"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["linked_session"] = SessionNote.objects.filter(appointment=self.object).first()
        return context


class AppointmentCreateView(TherapistRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "crm/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["therapist"] = self.request.user
        return kwargs


class AppointmentUpdateView(AppointmentCreateView, UpdateView):
    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user)


class AppointmentDeleteView(TherapistRequiredMixin, DeleteView):
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:appointment_list")

    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user)


class SessionListView(TherapistRequiredMixin, ListView):
    template_name = "crm/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        return session_queryset_for(self.request.user)


class SessionDetailView(TherapistRequiredMixin, DetailView):
    template_name = "crm/session_detail.html"
    context_object_name = "session"

    def get_queryset(self):
        return session_queryset_for(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["score_summary"] = session_score_summary(self.object)
        return context


class SessionCreateView(TherapistRequiredMixin, CreateView):
    model = SessionNote
    form_class = SessionNoteForm
    template_name = "crm/session_form.html"

    def _appointment_from_param(self):
        """Return the Appointment from ?appointment= if valid for this therapist (cached)."""
        if hasattr(self, "_appt_param_cache"):
            return self._appt_param_cache
        pk = self.request.GET.get("appointment")
        if not pk:
            self._appt_param_cache = None
        else:
            try:
                self._appt_param_cache = Appointment.objects.filter(
                    patient__therapist=self.request.user, pk=pk
                ).select_related("patient").get()
            except (Appointment.DoesNotExist, ValueError):
                self._appt_param_cache = None
        return self._appt_param_cache

    def get_initial(self):
        initial = super().get_initial()
        if not getattr(self, "object", None):
            appt = self._appointment_from_param()
            if appt:
                initial["appointment"] = appt.pk
                initial["patient"] = appt.patient_id
                initial["session_date"] = appt.starts_at.date()
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["therapist"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        existing_scores = {}
        if getattr(self, "object", None):
            existing_scores = {
                score.criterion_id: score.value
                for score in self.object.scores.select_related("criterion")
            }
        context["criteria"] = [
            {"criterion": criterion, "value": existing_scores.get(criterion.pk, "")}
            for criterion in criteria_for(self.request.user)
        ]
        if not getattr(self, "object", None):
            context["linked_appointment"] = self._appointment_from_param()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        save_scores_for_session(self.object, self.request.POST)
        return response


class SessionUpdateView(SessionCreateView, UpdateView):
    def get_queryset(self):
        return session_queryset_for(self.request.user)


class SessionDeleteView(TherapistRequiredMixin, DeleteView):
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:session_list")

    def get_queryset(self):
        return session_queryset_for(self.request.user)


class CriterionListView(TherapistRequiredMixin, ListView):
    template_name = "crm/criterion_list.html"
    context_object_name = "criteria"

    def get_queryset(self):
        return ScoringCriterion.objects.filter(therapist=self.request.user)


class CriterionCreateView(TherapistRequiredMixin, CreateView):
    model = ScoringCriterion
    form_class = ScoringCriterionForm
    template_name = "crm/form.html"
    success_url = reverse_lazy("crm:criterion_list")

    def form_valid(self, form):
        form.instance.therapist = self.request.user
        return super().form_valid(form)


class CriterionUpdateView(TherapistRequiredMixin, UpdateView):
    form_class = ScoringCriterionForm
    template_name = "crm/form.html"
    success_url = reverse_lazy("crm:criterion_list")

    def get_queryset(self):
        return ScoringCriterion.objects.filter(therapist=self.request.user)


class CriterionDeleteView(TherapistRequiredMixin, DeleteView):
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:criterion_list")

    def get_queryset(self):
        return ScoringCriterion.objects.filter(therapist=self.request.user)
