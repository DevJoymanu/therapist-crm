from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as _DjangoLoginView
from django.urls import reverse
from django.views.generic import TemplateView

from booking.models import AppointmentRequest
from core.ratelimit import is_rate_limited, rate_limited_response
from core.services import dashboard_context
from patients.services import patient_queryset_for


class TherapistRequiredMixin(LoginRequiredMixin):
    login_url = "login"


class SendBookingLinkMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_patients"] = (
            patient_queryset_for(self.request.user)
            .filter(is_active=True)
            .order_by("last_name", "first_name")
        )
        context["booking_portal_url"] = self.request.build_absolute_uri(
            reverse("booking:booking_portal", kwargs={"username": self.request.user.username})
        )
        return context


class DashboardView(SendBookingLinkMixin, TherapistRequiredMixin, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(dashboard_context(self.request.user))
        context["pending_requests"] = AppointmentRequest.objects.filter(
            therapist=self.request.user, status=AppointmentRequest.Status.PENDING
        ).order_by("preferred_date")[:5]
        return context


class RateLimitedLoginView(_DjangoLoginView):
    def post(self, request, *args, **kwargs):
        if is_rate_limited(
            request,
            prefix="login",
            max_hits=settings.RATE_LIMIT_LOGIN_ATTEMPTS,
            window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
        ):
            return rate_limited_response(request)
        return super().post(request, *args, **kwargs)
