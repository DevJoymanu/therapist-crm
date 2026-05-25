from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from appointments.models import Appointment
from core.views import SendBookingLinkMixin, TherapistRequiredMixin

from .forms import ScoringCriterionForm, SessionNoteForm
from .models import ScoringCriterion, SessionNote
from .services import criteria_for, save_scores_for_session, session_queryset_for, session_score_summary


class SessionListView(SendBookingLinkMixin, TherapistRequiredMixin, ListView):
    template_name = "crm/session_list.html"
    context_object_name = "sessions"

    def get_queryset(self):
        return session_queryset_for(self.request.user)


class SessionDetailView(SendBookingLinkMixin, TherapistRequiredMixin, DetailView):
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
        if hasattr(self, "_appt_param_cache"):
            return self._appt_param_cache
        pk = self.request.GET.get("appointment")
        if not pk:
            self._appt_param_cache = None
        else:
            try:
                self._appt_param_cache = (
                    Appointment.objects.filter(patient__therapist=self.request.user, pk=pk)
                    .select_related("patient")
                    .get()
                )
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
    success_url = reverse_lazy("notes:session_list")

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
    success_url = reverse_lazy("notes:criterion_list")

    def form_valid(self, form):
        form.instance.therapist = self.request.user
        return super().form_valid(form)


class CriterionUpdateView(TherapistRequiredMixin, UpdateView):
    form_class = ScoringCriterionForm
    template_name = "crm/form.html"
    success_url = reverse_lazy("notes:criterion_list")

    def get_queryset(self):
        return ScoringCriterion.objects.filter(therapist=self.request.user)


class CriterionDeleteView(TherapistRequiredMixin, DeleteView):
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("notes:criterion_list")

    def get_queryset(self):
        return ScoringCriterion.objects.filter(therapist=self.request.user)
