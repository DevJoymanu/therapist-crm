import datetime
import re
import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as _DjangoLoginView
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .ratelimit import get_client_ip, is_rate_limited, rate_limited_response
from .forms import (
    AppointmentForm,
    ApproveRequestForm,
    ClientConsentForm,
    NewClientBookingForm,
    PatientForm,
    PersonalizedBookingForm,
    ReturningClientBookingForm,
    ScoringCriterionForm,
    SessionNoteForm,
)
from .models import (
    Appointment,
    AppointmentRequest,
    ClientConsent,
    Patient,
    ScoringCriterion,
    SessionNote,
    ShareableLink,
)
from .services import (
    calculate_session_score,
    criteria_for,
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


class RateLimitedLoginView(_DjangoLoginView):
    """Django's LoginView with per-IP brute-force protection."""

    def post(self, request, *args, **kwargs):
        if is_rate_limited(
            request,
            prefix="login",
            max_hits=settings.RATE_LIMIT_LOGIN_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
        ):
            return rate_limited_response(request)
        return super().post(request, *args, **kwargs)


def _honeypot_triggered(request) -> bool:
    """Return True when a bot-trap field has been filled in."""
    return bool(request.POST.get("pot", "").strip())


def _honeypot_response() -> HttpResponse:
    """Return a silent 200 so bots think they succeeded."""
    return HttpResponse(
        "<!doctype html><html><head><title>Thank you</title></head>"
        "<body><p>Your request has been received.</p></body></html>"
    )


# ── CRM views ─────────────────────────────────────────────────────────────────

class DashboardView(TherapistRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(dashboard_context(self.request.user))
        context["pending_requests"] = AppointmentRequest.objects.filter(
            therapist=self.request.user, status=AppointmentRequest.Status.PENDING
        ).order_by("preferred_date")[:5]
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
        if hasattr(self, "_appt_param_cache"):
            return self._appt_param_cache
        pk = self.request.GET.get("appointment")
        if not pk:
            self._appt_param_cache = None
        else:
            try:
                self._appt_param_cache = (
                    Appointment.objects.filter(
                        patient__therapist=self.request.user, pk=pk
                    )
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


class ConsentFormView(FormView):
    template_name = "crm/consent_form.html"
    form_class = ClientConsentForm

    def _get_consent(self):
        try:
            return ClientConsent.objects.select_related("patient").get(
                token=self.kwargs["token"]
            )
        except ClientConsent.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consent = self._get_consent()
        context["consent"] = consent
        context["already_signed"] = consent.is_signed
        return context

    def form_valid(self, form):
        consent = self._get_consent()
        if not consent.is_signed:
            consent.client_name = form.cleaned_data["client_name"]
            consent.client_signed_date = form.cleaned_data["client_signed_date"]
            consent.save(update_fields=["client_name", "client_signed_date", "updated_at"])
        return redirect(reverse("crm:consent_done", kwargs={"token": consent.token}))


class ConsentDoneView(TemplateView):
    template_name = "crm/consent_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["consent"] = ClientConsent.objects.select_related("patient").get(
                token=self.kwargs["token"]
            )
        except ClientConsent.DoesNotExist:
            raise Http404
        return context


# ── Public booking portal ─────────────────────────────────────────────────────

class BookingPortalView(View):
    template_name = "crm/booking_portal.html"

    def _get_therapist(self, username):
        User = get_user_model()
        return get_object_or_404(User, username=username)

    def get(self, request, username):
        therapist = self._get_therapist(username)
        return render(request, self.template_name, {
            "therapist": therapist,
            "new_form": NewClientBookingForm(),
            "returning_form": ReturningClientBookingForm(),
            "active_tab": "new",
        })

    def post(self, request, username):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(
            request,
            prefix="booking_portal",
            max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW,
        ):
            return rate_limited_response(request)
        therapist = self._get_therapist(username)
        client_type = request.POST.get("client_type", "new")

        if client_type == "new":
            form = NewClientBookingForm(request.POST)
            if form.is_valid():
                req = AppointmentRequest.objects.create(
                    therapist=therapist,
                    is_new_client=True,
                    client_first_name=form.cleaned_data["first_name"],
                    client_last_name=form.cleaned_data["last_name"],
                    client_phone=form.cleaned_data["phone"],
                    client_email=form.cleaned_data.get("email", ""),
                    preferred_date=form.cleaned_data["preferred_date"],
                    preferred_time_slot=form.cleaned_data.get("preferred_time_slot", ""),
                    reason=form.cleaned_data.get("reason", ""),
                )
                return redirect(reverse("crm:booking_confirm", kwargs={"token": req.token}))
            return render(request, self.template_name, {
                "therapist": therapist,
                "new_form": form,
                "returning_form": ReturningClientBookingForm(),
                "active_tab": "new",
            })

        # returning client
        form = ReturningClientBookingForm(request.POST)
        if form.is_valid():
            try:
                patient = Patient.objects.get(
                    pk=form.cleaned_data["client_id"],
                    last_name__iexact=form.cleaned_data["last_name"],
                    therapist=therapist,
                )
            except Patient.DoesNotExist:
                form.add_error("client_id", "Client ID and surname do not match our records.")
            else:
                req = AppointmentRequest.objects.create(
                    therapist=therapist,
                    patient=patient,
                    is_new_client=False,
                    client_first_name=patient.first_name,
                    client_last_name=patient.last_name,
                    client_phone=patient.phone,
                    client_email=patient.email,
                    preferred_date=form.cleaned_data["preferred_date"],
                    preferred_time_slot=form.cleaned_data.get("preferred_time_slot", ""),
                    reason=form.cleaned_data.get("reason", ""),
                )
                return redirect(reverse("crm:booking_confirm", kwargs={"token": req.token}))
        return render(request, self.template_name, {
            "therapist": therapist,
            "new_form": NewClientBookingForm(),
            "returning_form": form,
            "active_tab": "returning",
        })


class PersonalizedBookingView(View):
    template_name = "crm/booking_personal.html"

    def _get_patient(self, token):
        return get_object_or_404(Patient, booking_token=token)

    def get(self, request, token):
        patient = self._get_patient(token)
        return render(request, self.template_name, {
            "patient": patient,
            "form": PersonalizedBookingForm(),
        })

    def post(self, request, token):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(
            request,
            prefix="personal_booking",
            max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW,
        ):
            return rate_limited_response(request)
        patient = self._get_patient(token)
        form = PersonalizedBookingForm(request.POST)
        if form.is_valid():
            req = AppointmentRequest.objects.create(
                therapist=patient.therapist,
                patient=patient,
                is_new_client=False,
                client_first_name=patient.first_name,
                client_last_name=patient.last_name,
                client_phone=patient.phone,
                client_email=patient.email,
                preferred_date=form.cleaned_data["preferred_date"],
                preferred_time_slot=form.cleaned_data.get("preferred_time_slot", ""),
                reason=form.cleaned_data.get("reason", ""),
            )
            return redirect(reverse("crm:booking_confirm", kwargs={"token": req.token}))
        return render(request, self.template_name, {"patient": patient, "form": form})


class BookingConfirmView(TemplateView):
    template_name = "crm/booking_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["booking_request"] = get_object_or_404(
            AppointmentRequest, token=self.kwargs["token"]
        )
        return context


# ── Therapist booking management ──────────────────────────────────────────────

class BookingRequestsView(TherapistRequiredMixin, TemplateView):
    template_name = "crm/booking_requests.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = AppointmentRequest.objects.filter(
            therapist=self.request.user
        ).select_related("patient")
        context["pending"] = qs.filter(status=AppointmentRequest.Status.PENDING).order_by(
            "preferred_date"
        )
        context["resolved"] = qs.exclude(
            status=AppointmentRequest.Status.PENDING
        ).order_by("-updated_at")[:20]
        context["booking_url"] = self.request.build_absolute_uri(
            reverse("crm:booking_portal", kwargs={"username": self.request.user.username})
        )
        return context


class ApproveRequestView(TherapistRequiredMixin, View):
    template_name = "crm/approve_form.html"

    def _get_req(self, pk):
        return get_object_or_404(
            AppointmentRequest,
            pk=pk,
            therapist=self.request.user,
            status=AppointmentRequest.Status.PENDING,
        )

    def get(self, request, pk):
        req = self._get_req(pk)
        initial_dt = datetime.datetime.combine(req.preferred_date, datetime.time(9, 0))
        form = ApproveRequestForm(initial={"starts_at": initial_dt, "duration_minutes": 50})
        return render(request, self.template_name, {"req": req, "form": form})

    def post(self, request, pk):
        req = self._get_req(pk)
        form = ApproveRequestForm(request.POST)
        if form.is_valid():
            starts_at = timezone.make_aware(form.cleaned_data["starts_at"])
            duration = int(form.cleaned_data["duration_minutes"])
            ends_at = starts_at + datetime.timedelta(minutes=duration)

            if req.is_new_client:
                patient = Patient.objects.create(
                    therapist=request.user,
                    first_name=req.client_first_name,
                    last_name=req.client_last_name,
                    phone=req.client_phone,
                    email=req.client_email,
                )
                ClientConsent.objects.create(patient=patient)
                req.patient = patient

            appointment = Appointment.objects.create(
                patient=req.patient,
                starts_at=starts_at,
                ends_at=ends_at,
                location=form.cleaned_data.get("location", ""),
                status=Appointment.Status.SCHEDULED,
            )
            req.linked_appointment = appointment
            req.status = AppointmentRequest.Status.APPROVED
            req.save()
            messages.success(
                request,
                f"Appointment confirmed for {req.client_full_name} on "
                f"{starts_at.strftime('%b %d at %H:%M')}.",
            )
            return redirect(reverse("crm:booking_requests"))
        return render(request, self.template_name, {"req": req, "form": form})


class DeclineRequestView(TherapistRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(
            AppointmentRequest,
            pk=pk,
            therapist=request.user,
            status=AppointmentRequest.Status.PENDING,
        )
        req.status = AppointmentRequest.Status.DECLINED
        req.therapist_response = request.POST.get("decline_reason", "")
        req.save(update_fields=["status", "therapist_response", "updated_at"])
        messages.success(request, f"Request from {req.client_full_name} has been declined.")
        return redirect(reverse("crm:booking_requests"))


# ── Shareable expiring links ──────────────────────────────────────────────────

_LINK_EXPIRY_DAYS = 7


class GenerateLinkView(TherapistRequiredMixin, View):
    """
    POST /patients/<pk>/links/<link_type>/
    Creates a fresh ShareableLink with a 7-day expiry and returns an HTML
    partial that HTMX swaps into the page.
    """

    def post(self, request, pk, link_type):
        if link_type not in (ShareableLink.LinkType.CONSENT, ShareableLink.LinkType.BOOKING):
            raise Http404
        if is_rate_limited(
            request,
            prefix="gen_link",
            max_hits=settings.RATE_LIMIT_GENLINK_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_GENLINK_WINDOW,
            per_user=True,
        ):
            return HttpResponse("Too many link generations. Please wait before generating more.", status=429)
        patient = get_object_or_404(Patient, pk=pk, therapist=request.user)
        link = ShareableLink.objects.create(
            patient=patient,
            link_type=link_type,
            expires_at=timezone.now() + datetime.timedelta(days=_LINK_EXPIRY_DAYS),
        )
        url = request.build_absolute_uri(link.get_absolute_url())
        return render(request, "crm/partials/link_generated.html", {
            "url": url,
            "link": link,
            "generate_url": reverse(
                "crm:generate_link", kwargs={"pk": patient.pk, "link_type": link_type}
            ),
        })


class SharedLinkView(View):
    """
    Public-facing /link/<uuid:token>/ — validates expiry then renders
    the consent form or personalized booking form.
    """

    def _get_link(self, token):
        return get_object_or_404(
            ShareableLink.objects.select_related("patient"),
            token=token,
        )

    def _consent(self, patient):
        try:
            return patient.consent
        except Exception:
            return ClientConsent.objects.create(patient=patient)

    def get(self, request, token):
        link = self._get_link(token)
        if link.is_expired:
            return render(request, "crm/link_expired.html", {"link": link}, status=410)

        context = {"link": link}
        if link.link_type == ShareableLink.LinkType.CONSENT:
            consent = self._consent(link.patient)
            context["consent"] = consent
            context["already_signed"] = consent.is_signed
            if not consent.is_signed:
                context["form"] = ClientConsentForm()
        else:
            context["form"] = PersonalizedBookingForm()
        return render(request, "crm/shared_link.html", context)

    def post(self, request, token):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(
            request,
            prefix="shared_link",
            max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW,
        ):
            return rate_limited_response(request)
        link = self._get_link(token)
        if link.is_expired:
            return render(request, "crm/link_expired.html", {"link": link}, status=410)

        if link.link_type == ShareableLink.LinkType.CONSENT:
            consent = self._consent(link.patient)
            if consent.is_signed:
                return redirect(reverse("crm:consent_done", kwargs={"token": consent.token}))
            form = ClientConsentForm(request.POST)
            if form.is_valid():
                consent.client_name = form.cleaned_data["client_name"]
                consent.client_signed_date = form.cleaned_data["client_signed_date"]
                consent.save(update_fields=["client_name", "client_signed_date", "updated_at"])
                return redirect(reverse("crm:consent_done", kwargs={"token": consent.token}))
            return render(request, "crm/shared_link.html", {
                "link": link, "consent": consent, "form": form,
            })

        # booking
        form = PersonalizedBookingForm(request.POST)
        if form.is_valid():
            patient = link.patient
            req = AppointmentRequest.objects.create(
                therapist=patient.therapist,
                patient=patient,
                is_new_client=False,
                client_first_name=patient.first_name,
                client_last_name=patient.last_name,
                client_phone=patient.phone,
                client_email=patient.email,
                preferred_date=form.cleaned_data["preferred_date"],
                preferred_time_slot=form.cleaned_data.get("preferred_time_slot", ""),
                reason=form.cleaned_data.get("reason", ""),
            )
            return redirect(reverse("crm:booking_confirm", kwargs={"token": req.token}))
        return render(request, "crm/shared_link.html", {"link": link, "form": form})


# ── WhatsApp booking link ─────────────────────────────────────────────────────

def _clean_phone_for_wa(raw: str) -> str:
    """
    Strip everything except digits from the phone number.
    wa.me expects the international number without the leading +.
    Returns an empty string if the result is too short to be valid.
    """
    digits = re.sub(r"[^\d]", "", raw or "")
    return digits if len(digits) >= 7 else ""


class WhatsAppBookingLinkView(TherapistRequiredMixin, View):
    """
    GET /patients/<pk>/whatsapp/
    Creates a fresh expiring booking ShareableLink, builds a pre-filled
    WhatsApp message, and redirects to wa.me so WhatsApp opens directly.
    Opens in a new tab from the patient list (target="_blank" bypasses HTMX).
    """

    def get(self, request, pk):
        if is_rate_limited(
            request,
            prefix="wa_link",
            max_hits=settings.RATE_LIMIT_GENLINK_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_GENLINK_WINDOW,
            per_user=True,
        ):
            return HttpResponse("Too many link generations. Please wait before sending more.", status=429)

        patient = get_object_or_404(Patient, pk=pk, therapist=request.user)

        link = ShareableLink.objects.create(
            patient=patient,
            link_type=ShareableLink.LinkType.BOOKING,
            expires_at=timezone.now() + datetime.timedelta(days=_LINK_EXPIRY_DAYS),
        )
        booking_url = request.build_absolute_uri(link.get_absolute_url())
        expiry = link.expires_at.strftime("%d %B %Y")

        message = (
            f"Hello {patient.first_name},\n\n"
            f"Please use the link below to request your appointment with "
            f"Yanrol Systemic Family Counselling Services & Therapy:\n\n"
            f"{booking_url}\n\n"
            f"This link expires on {expiry}.\n\n"
            f"Please reply or call us if you have any questions."
        )

        phone = _clean_phone_for_wa(patient.phone)
        base = f"https://wa.me/{phone}" if phone else "https://wa.me"
        whatsapp_url = f"{base}?text={urllib.parse.quote(message)}"

        return HttpResponseRedirect(whatsapp_url)
