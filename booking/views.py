import datetime
import re
import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from appointments.models import Appointment
from core.ratelimit import is_rate_limited, rate_limited_response
from core.views import SendBookingLinkMixin, TherapistRequiredMixin
from patients.forms import ClientConsentForm, ClientIntakeForm, NewClientFullForm
from patients.models import ClientConsent, Patient

from .forms import ApproveRequestForm, PersonalizedBookingForm
from .models import AppointmentRequest, ShareableLink

_LINK_EXPIRY_DAYS = 7


def _honeypot_triggered(request) -> bool:
    return bool(request.POST.get("pot", "").strip())


def _honeypot_response() -> HttpResponse:
    return HttpResponse(
        "<!doctype html><html><head><title>Thank you</title></head>"
        "<body><p>Your request has been received.</p></body></html>"
    )


def _has_appointment_conflict(therapist, preferred_date, preferred_time_slot: str) -> bool:
    slot_ranges = {"morning": (8, 12), "afternoon": (12, 17), "evening": (17, 23)}
    if not preferred_time_slot or preferred_time_slot not in slot_ranges:
        return False
    start_h, end_h = slot_ranges[preferred_time_slot]
    start_dt = timezone.make_aware(datetime.datetime.combine(preferred_date, datetime.time(start_h, 0)))
    end_dt = timezone.make_aware(datetime.datetime.combine(preferred_date, datetime.time(end_h, 0)))
    return Appointment.objects.filter(
        patient__therapist=therapist,
        starts_at__gte=start_dt,
        starts_at__lt=end_dt,
        status=Appointment.Status.SCHEDULED,
    ).exists()


def _clean_phone_for_wa(raw: str) -> str:
    digits = re.sub(r"[^\d]", "", raw or "")
    return digits if len(digits) >= 7 else ""


class ConsentFormView(View):
    template_name = "crm/consent_form.html"

    def _get_consent(self):
        try:
            return ClientConsent.objects.select_related("patient").get(token=self.kwargs["token"])
        except ClientConsent.DoesNotExist:
            raise Http404

    def get(self, request, token):
        consent = self._get_consent()
        return render(request, self.template_name, {"form": ClientConsentForm(), "consent": consent, "already_signed": consent.is_signed})

    def post(self, request, token):
        consent = self._get_consent()
        form = ClientConsentForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "consent": consent, "already_signed": consent.is_signed})
        if not consent.is_signed:
            consent.client_name = form.cleaned_data["client_name"]
            consent.client_signed_date = form.cleaned_data["client_signed_date"]
            consent.save(update_fields=["client_name", "client_signed_date", "updated_at"])
        return redirect(reverse("booking:consent_done", kwargs={"token": consent.token}))


class ConsentDoneView(TemplateView):
    template_name = "crm/consent_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["consent"] = ClientConsent.objects.select_related("patient").get(token=self.kwargs["token"])
        except ClientConsent.DoesNotExist:
            raise Http404
        return context


class BookingPortalView(View):
    template_name = "crm/booking_portal.html"

    def _get_therapist(self, username):
        User = get_user_model()
        return get_object_or_404(User, username=username)

    def get(self, request, username):
        therapist = self._get_therapist(username)
        return render(request, self.template_name, {
            "therapist": therapist,
            "intake_form": NewClientFullForm(),
            "consent_form": ClientConsentForm(),
            "appt_form": PersonalizedBookingForm(),
        })

    def post(self, request, username):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(request, prefix="booking_portal", max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS, window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW):
            return rate_limited_response(request)
        therapist = self._get_therapist(username)
        client_id_str = request.POST.get("client_id", "").strip()
        if client_id_str:
            try:
                patient = Patient.objects.get(pk=int(client_id_str), therapist=therapist, is_active=True)
                return redirect(reverse("booking:booking_returning", kwargs={"username": username, "patient_pk": patient.pk}))
            except (ValueError, Patient.DoesNotExist):
                pass
        qs = "?id_not_found=1" if client_id_str else ""
        return redirect(reverse("booking:booking_new_client", kwargs={"username": username}) + qs)


class BookingCheckView(View):
    def post(self, request, username):
        if is_rate_limited(request, "booking_check", max_hits=20, window_seconds=60):
            return HttpResponse("<p class='mt-3 text-center text-xs text-rose-500'>Too many requests — please slow down.</p>")
        User = get_user_model()
        therapist = get_object_or_404(User, username=username)
        client_id_str = request.POST.get("client_id", "").strip()
        if not client_id_str:
            return render(request, "crm/partials/booking_check_empty.html", {"therapist": therapist})
        try:
            patient = Patient.objects.get(pk=int(client_id_str), therapist=therapist, is_active=True)
        except (ValueError, Patient.DoesNotExist):
            return render(request, "crm/partials/booking_check_not_found.html", {"therapist": therapist, "client_id_str": client_id_str})
        try:
            consent_signed = patient.consent.is_signed
        except Exception:
            consent_signed = False
        response = render(request, "crm/partials/booking_check_found.html", {
            "therapist": therapist, "patient": patient,
            "appt_form": PersonalizedBookingForm(),
            "consent_form": ClientConsentForm() if not consent_signed else None,
            "consent_signed": consent_signed,
        })
        response["HX-Retarget"] = "#booking-form-area"
        response["HX-Reswap"] = "innerHTML"
        return response


class BookingReturningView(View):
    template_name = "crm/booking_returning.html"

    def _get_objects(self, username, patient_pk):
        User = get_user_model()
        therapist = get_object_or_404(User, username=username)
        patient = get_object_or_404(Patient, pk=patient_pk, therapist=therapist, is_active=True)
        try:
            consent_signed = patient.consent.is_signed
        except Exception:
            consent_signed = False
        return therapist, patient, consent_signed

    def get(self, request, username, patient_pk):
        therapist, patient, consent_signed = self._get_objects(username, patient_pk)
        return render(request, self.template_name, {
            "therapist": therapist, "patient": patient,
            "appt_form": PersonalizedBookingForm(),
            "consent_form": ClientConsentForm() if not consent_signed else None,
            "consent_signed": consent_signed,
        })

    def post(self, request, username, patient_pk):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(request, prefix="booking_returning", max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS, window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW):
            return rate_limited_response(request)
        therapist, patient, consent_signed = self._get_objects(username, patient_pk)
        appt_form = PersonalizedBookingForm(request.POST)
        consent_form = ClientConsentForm(request.POST) if not consent_signed else None
        forms_valid = appt_form.is_valid() and (consent_form.is_valid() if consent_form else True)
        if forms_valid:
            preferred_date = appt_form.cleaned_data["preferred_date"]
            preferred_slot = appt_form.cleaned_data.get("preferred_time_slot", "")
            if _has_appointment_conflict(therapist, preferred_date, preferred_slot):
                appt_form.add_error("preferred_date", "That time slot already has an appointment booked. Please choose a different date or time.")
            else:
                if consent_form:
                    try:
                        c = patient.consent
                    except Exception:
                        c = ClientConsent(patient=patient)
                    c.client_name = consent_form.cleaned_data["client_name"]
                    c.client_signed_date = consent_form.cleaned_data["client_signed_date"]
                    c.save()
                req = AppointmentRequest.objects.create(
                    therapist=therapist, patient=patient, is_new_client=False,
                    client_first_name=patient.first_name, client_last_name=patient.last_name,
                    client_phone=patient.phone, client_email=patient.email,
                    preferred_date=preferred_date, preferred_time_slot=preferred_slot,
                    reason=appt_form.cleaned_data.get("reason", ""),
                )
                return redirect(reverse("booking:booking_confirm", kwargs={"token": req.token}))
        return render(request, self.template_name, {
            "therapist": therapist, "patient": patient,
            "appt_form": appt_form, "consent_form": consent_form, "consent_signed": consent_signed,
        })


class BookingNewClientView(View):
    template_name = "crm/booking_new_client.html"

    def _get_therapist(self, username):
        User = get_user_model()
        return get_object_or_404(User, username=username)

    def get(self, request, username):
        therapist = self._get_therapist(username)
        return render(request, self.template_name, {
            "therapist": therapist,
            "id_not_found": request.GET.get("id_not_found") == "1",
            "intake_form": NewClientFullForm(),
            "consent_form": ClientConsentForm(),
            "appt_form": PersonalizedBookingForm(),
        })

    def post(self, request, username):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(request, prefix="booking_new_client", max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS, window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW):
            return rate_limited_response(request)
        therapist = self._get_therapist(username)
        intake_form = NewClientFullForm(request.POST)
        consent_form = ClientConsentForm(request.POST)
        appt_form = PersonalizedBookingForm(request.POST)
        all_valid = intake_form.is_valid() and consent_form.is_valid() and appt_form.is_valid()
        if all_valid:
            preferred_date = appt_form.cleaned_data["preferred_date"]
            preferred_slot = appt_form.cleaned_data.get("preferred_time_slot", "")
            if _has_appointment_conflict(therapist, preferred_date, preferred_slot):
                appt_form.add_error("preferred_date", "That time slot already has an appointment booked. Please choose a different date or time.")
                all_valid = False
        if all_valid:
            patient = intake_form.save(commit=False)
            patient.therapist = therapist
            patient.save()
            c = ClientConsent(patient=patient)
            c.client_name = consent_form.cleaned_data["client_name"]
            c.client_signed_date = consent_form.cleaned_data["client_signed_date"]
            c.save()
            req = AppointmentRequest.objects.create(
                therapist=therapist, patient=patient, is_new_client=True,
                client_first_name=patient.first_name, client_last_name=patient.last_name,
                client_phone=patient.phone, client_email=patient.email,
                preferred_date=preferred_date, preferred_time_slot=preferred_slot,
                reason=appt_form.cleaned_data.get("reason", ""),
            )
            return redirect(reverse("booking:booking_confirm", kwargs={"token": req.token}))
        return render(request, self.template_name, {
            "therapist": therapist, "id_not_found": False,
            "intake_form": intake_form, "consent_form": consent_form, "appt_form": appt_form,
        })


class PersonalizedBookingView(View):
    template_name = "crm/booking_personal.html"

    def _get_patient(self, token):
        return get_object_or_404(Patient, booking_token=token)

    def get(self, request, token):
        patient = self._get_patient(token)
        return render(request, self.template_name, {"patient": patient, "form": PersonalizedBookingForm()})

    def post(self, request, token):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(request, prefix="personal_booking", max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS, window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW):
            return rate_limited_response(request)
        patient = self._get_patient(token)
        form = PersonalizedBookingForm(request.POST)
        if form.is_valid():
            req = AppointmentRequest.objects.create(
                therapist=patient.therapist, patient=patient, is_new_client=False,
                client_first_name=patient.first_name, client_last_name=patient.last_name,
                client_phone=patient.phone, client_email=patient.email,
                preferred_date=form.cleaned_data["preferred_date"],
                preferred_time_slot=form.cleaned_data.get("preferred_time_slot", ""),
                reason=form.cleaned_data.get("reason", ""),
            )
            return redirect(reverse("booking:booking_confirm", kwargs={"token": req.token}))
        return render(request, self.template_name, {"patient": patient, "form": form})


class BookingConfirmView(TemplateView):
    template_name = "crm/booking_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = get_object_or_404(AppointmentRequest, token=self.kwargs["token"])
        context["booking_request"] = req
        context["has_conflict"] = _has_appointment_conflict(req.therapist, req.preferred_date, req.preferred_time_slot)
        return context


class BookingRequestsView(SendBookingLinkMixin, TherapistRequiredMixin, TemplateView):
    template_name = "crm/booking_requests.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = AppointmentRequest.objects.filter(therapist=self.request.user).select_related("patient")
        context["pending"] = qs.filter(status=AppointmentRequest.Status.PENDING).order_by("preferred_date")
        context["resolved"] = qs.exclude(status=AppointmentRequest.Status.PENDING).order_by("-updated_at")[:20]
        context["booking_url"] = self.request.build_absolute_uri(
            reverse("booking:booking_portal", kwargs={"username": self.request.user.username})
        )
        return context


class ApproveRequestView(TherapistRequiredMixin, View):
    template_name = "crm/approve_form.html"

    def _get_req(self, pk):
        return get_object_or_404(AppointmentRequest, pk=pk, therapist=self.request.user, status=AppointmentRequest.Status.PENDING)

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
            if req.is_new_client and req.patient is None:
                patient = Patient.objects.create(
                    therapist=request.user,
                    first_name=req.client_first_name, last_name=req.client_last_name,
                    phone=req.client_phone, email=req.client_email,
                )
                ClientConsent.objects.create(patient=patient)
                req.patient = patient
            appointment = Appointment.objects.create(
                patient=req.patient, starts_at=starts_at, ends_at=ends_at,
                location=form.cleaned_data.get("location", ""),
                status=Appointment.Status.SCHEDULED,
            )
            req.linked_appointment = appointment
            req.status = AppointmentRequest.Status.APPROVED
            req.save()
            messages.success(request, f"Appointment confirmed for {req.client_full_name} on {starts_at.strftime('%b %d at %H:%M')}.")
            return redirect(reverse("booking:booking_requests"))
        return render(request, self.template_name, {"req": req, "form": form})


class DeclineRequestView(TherapistRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(AppointmentRequest, pk=pk, therapist=request.user, status=AppointmentRequest.Status.PENDING)
        req.status = AppointmentRequest.Status.DECLINED
        req.therapist_response = request.POST.get("decline_reason", "")
        req.save(update_fields=["status", "therapist_response", "updated_at"])
        messages.success(request, f"Request from {req.client_full_name} has been declined.")
        return redirect(reverse("booking:booking_requests"))


class DashboardSendBookingLinkView(TherapistRequiredMixin, View):
    def post(self, request):
        patient_pk = request.POST.get("patient_pk", "").strip()
        if not patient_pk:
            return HttpResponse("<p class='text-sm text-rose-600 py-2'>Please select a client first.</p>")
        if is_rate_limited(request, prefix="gen_link", max_hits=settings.RATE_LIMIT_GENLINK_ATTEMPTS, window_seconds=settings.RATE_LIMIT_GENLINK_WINDOW, per_user=True):
            return HttpResponse("<p class='text-sm text-rose-600 py-2'>Too many link generations. Please wait.</p>", status=429)
        patient = get_object_or_404(Patient, pk=patient_pk, therapist=request.user)
        link = ShareableLink.objects.create(
            patient=patient, link_type=ShareableLink.LinkType.BOOKING,
            expires_at=timezone.now() + datetime.timedelta(days=_LINK_EXPIRY_DAYS),
        )
        url = request.build_absolute_uri(link.get_absolute_url())
        message = (
            f"Hello {patient.first_name},\n\nPlease use the link below to request your appointment with "
            f"Yanrol Systemic Family Counselling Services & Therapy:\n\n{url}\n\n"
            f"This link expires on {link.expires_at.strftime('%d %B %Y')}."
        )
        phone = _clean_phone_for_wa(patient.phone)
        wa_base = f"https://wa.me/{phone}" if phone else "https://wa.me"
        wa_url = f"{wa_base}?text={urllib.parse.quote(message)}"
        return render(request, "crm/partials/send_booking_link_result.html", {"patient": patient, "url": url, "wa_url": wa_url, "link": link})


class GenerateLinkView(TherapistRequiredMixin, View):
    def post(self, request, pk, link_type):
        if link_type not in (ShareableLink.LinkType.CONSENT, ShareableLink.LinkType.BOOKING, ShareableLink.LinkType.INTAKE):
            raise Http404
        if is_rate_limited(request, prefix="gen_link", max_hits=settings.RATE_LIMIT_GENLINK_ATTEMPTS, window_seconds=settings.RATE_LIMIT_GENLINK_WINDOW, per_user=True):
            return HttpResponse("Too many link generations. Please wait before generating more.", status=429)
        patient = get_object_or_404(Patient, pk=pk, therapist=request.user)
        link = ShareableLink.objects.create(
            patient=patient, link_type=link_type,
            expires_at=timezone.now() + datetime.timedelta(days=_LINK_EXPIRY_DAYS),
        )
        url = request.build_absolute_uri(link.get_absolute_url())
        return render(request, "crm/partials/link_generated.html", {
            "url": url, "link": link,
            "generate_url": reverse("booking:generate_link", kwargs={"pk": patient.pk, "link_type": link_type}),
        })


class SharedLinkView(View):
    def _get_link(self, token):
        return get_object_or_404(ShareableLink.objects.select_related("patient"), token=token)

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
        elif link.link_type == ShareableLink.LinkType.INTAKE:
            context["form"] = ClientIntakeForm(instance=link.patient)
            context["already_submitted"] = bool(link.patient.intake_submitted_at)
        else:
            context["form"] = PersonalizedBookingForm()
        return render(request, "crm/shared_link.html", context)

    def post(self, request, token):
        if _honeypot_triggered(request):
            return _honeypot_response()
        if is_rate_limited(request, prefix="shared_link", max_hits=settings.RATE_LIMIT_PUBLIC_ATTEMPTS, window_seconds=settings.RATE_LIMIT_PUBLIC_WINDOW):
            return rate_limited_response(request)
        link = self._get_link(token)
        if link.is_expired:
            return render(request, "crm/link_expired.html", {"link": link}, status=410)
        if link.link_type == ShareableLink.LinkType.CONSENT:
            consent = self._consent(link.patient)
            if consent.is_signed:
                return redirect(reverse("booking:consent_done", kwargs={"token": consent.token}))
            form = ClientConsentForm(request.POST)
            if form.is_valid():
                consent.client_name = form.cleaned_data["client_name"]
                consent.client_signed_date = form.cleaned_data["client_signed_date"]
                consent.save(update_fields=["client_name", "client_signed_date", "updated_at"])
                return redirect(reverse("booking:consent_done", kwargs={"token": consent.token}))
            return render(request, "crm/shared_link.html", {"link": link, "consent": consent, "form": form})
        if link.link_type == ShareableLink.LinkType.INTAKE:
            form = ClientIntakeForm(request.POST, instance=link.patient)
            if form.is_valid():
                patient = form.save(commit=False)
                patient.intake_submitted_at = timezone.now()
                patient.save()
                return redirect(link.get_absolute_url())
            return render(request, "crm/shared_link.html", {"link": link, "form": form, "already_submitted": bool(link.patient.intake_submitted_at)})
        form = PersonalizedBookingForm(request.POST)
        if form.is_valid():
            patient = link.patient
            req = AppointmentRequest.objects.create(
                therapist=patient.therapist, patient=patient, is_new_client=False,
                client_first_name=patient.first_name, client_last_name=patient.last_name,
                client_phone=patient.phone, client_email=patient.email,
                preferred_date=form.cleaned_data["preferred_date"],
                preferred_time_slot=form.cleaned_data.get("preferred_time_slot", ""),
                reason=form.cleaned_data.get("reason", ""),
            )
            return redirect(reverse("booking:booking_confirm", kwargs={"token": req.token}))
        return render(request, "crm/shared_link.html", {"link": link, "form": form})


class WhatsAppBookingLinkView(TherapistRequiredMixin, View):
    def get(self, request, pk):
        if is_rate_limited(request, prefix="wa_link", max_hits=settings.RATE_LIMIT_GENLINK_ATTEMPTS, window_seconds=settings.RATE_LIMIT_GENLINK_WINDOW, per_user=True):
            return HttpResponse("Too many link generations. Please wait before sending more.", status=429)
        patient = get_object_or_404(Patient, pk=pk, therapist=request.user)
        link = ShareableLink.objects.create(
            patient=patient, link_type=ShareableLink.LinkType.BOOKING,
            expires_at=timezone.now() + datetime.timedelta(days=_LINK_EXPIRY_DAYS),
        )
        booking_url = request.build_absolute_uri(link.get_absolute_url())
        expiry = link.expires_at.strftime("%d %B %Y")
        message = (
            f"Hello {patient.first_name},\n\nPlease use the link below to request your appointment with "
            f"Yanrol Systemic Family Counselling Services & Therapy:\n\n{booking_url}\n\n"
            f"This link expires on {expiry}.\n\nPlease reply or call us if you have any questions."
        )
        phone = _clean_phone_for_wa(patient.phone)
        base = f"https://wa.me/{phone}" if phone else "https://wa.me"
        whatsapp_url = f"{base}?text={urllib.parse.quote(message)}"
        return HttpResponseRedirect(whatsapp_url)
