import calendar as _cal
import datetime

from django.http import Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from booking.models import AppointmentRequest
from core.views import SendBookingLinkMixin, TherapistRequiredMixin
from notes.models import SessionNote

from .forms import AppointmentForm
from .models import Appointment


class AppointmentListView(SendBookingLinkMixin, TherapistRequiredMixin, ListView):
    template_name = "crm/appointment_list.html"
    context_object_name = "appointments"

    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user).select_related("patient")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["today_appointments"] = (
            Appointment.objects.filter(
                patient__therapist=self.request.user,
                starts_at__date=timezone.localdate(),
            )
            .select_related("patient")
            .order_by("starts_at")
        )
        return context


class AppointmentDetailView(SendBookingLinkMixin, TherapistRequiredMixin, DetailView):
    template_name = "crm/appointment_detail.html"
    context_object_name = "appointment"

    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user).select_related("patient")

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
    success_url = reverse_lazy("appointments:appointment_list")

    def get_queryset(self):
        return Appointment.objects.filter(patient__therapist=self.request.user)


class CalendarView(SendBookingLinkMixin, TherapistRequiredMixin, TemplateView):
    template_name = "crm/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month_param = self.request.GET.get("month")
        today = timezone.localdate()
        try:
            if month_param:
                y, m = [int(x) for x in month_param.split("-")]
                current_month = datetime.date(y, m, 1)
            else:
                current_month = today.replace(day=1)
        except (ValueError, AttributeError):
            current_month = today.replace(day=1)

        y, m = current_month.year, current_month.month
        prev_dt = (current_month - datetime.timedelta(days=1)).replace(day=1)
        last_day = _cal.monthrange(y, m)[1]
        next_dt = current_month.replace(day=last_day) + datetime.timedelta(days=1)
        cal_obj = _cal.Calendar(firstweekday=0)
        month_weeks = cal_obj.monthdatescalendar(y, m)
        first_visible = month_weeks[0][0]
        last_visible = month_weeks[-1][-1]

        appointments = (
            Appointment.objects.filter(
                patient__therapist=self.request.user,
                starts_at__date__gte=first_visible,
                starts_at__date__lte=last_visible,
            )
            .select_related("patient")
            .order_by("starts_at")
        )
        requests = (
            AppointmentRequest.objects.filter(
                therapist=self.request.user,
                preferred_date__gte=first_visible,
                preferred_date__lte=last_visible,
            )
            .select_related("patient")
            .order_by("preferred_date", "preferred_time_slot")
        )

        appt_by_date = {}
        for appt in appointments:
            appt_by_date.setdefault(appt.starts_at.date(), []).append(appt)

        req_by_date = {}
        for req in requests:
            req_by_date.setdefault(req.preferred_date, []).append(req)

        weeks = []
        for week in month_weeks:
            week_days = []
            for day in week:
                appts = appt_by_date.get(day, [])
                reqs = req_by_date.get(day, [])
                total = len(appts) + len(reqs)
                mini_items = []
                for a in appts[:3]:
                    mini_items.append({"kind": "appointment", "label": f"{a.starts_at.strftime('%H:%M')} {a.patient.first_name}", "status": a.status})
                remaining = max(0, 3 - len(mini_items))
                for r in reqs[:remaining]:
                    name = r.patient.first_name if r.patient else r.client_first_name
                    mini_items.append({"kind": "request", "label": name, "req_status": r.status})
                week_days.append({
                    "date": day, "date_str": day.isoformat(), "in_month": day.month == m,
                    "is_today": day == today, "mini_items": mini_items,
                    "total": total, "overflow": max(0, total - 3),
                })
            weeks.append(week_days)

        context.update({
            "current_month": current_month,
            "prev_month": prev_dt.strftime("%Y-%m"),
            "next_month": next_dt.strftime("%Y-%m"),
            "weeks": weeks,
            "today": today,
        })
        return context


class CalendarDayView(TherapistRequiredMixin, View):
    def get(self, request, date_str):
        try:
            day = datetime.date.fromisoformat(date_str)
        except ValueError:
            raise Http404

        appointments = (
            Appointment.objects.filter(patient__therapist=request.user, starts_at__date=day)
            .select_related("patient")
            .order_by("starts_at")
        )
        reqs = (
            AppointmentRequest.objects.filter(therapist=request.user, preferred_date=day)
            .select_related("patient")
            .order_by("preferred_time_slot")
        )
        return render(request, "crm/partials/calendar_day_panel.html", {
            "day": day, "appointments": appointments, "requests": reqs,
        })
