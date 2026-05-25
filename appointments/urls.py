from django.urls import path

from .views import (
    AppointmentCreateView,
    AppointmentDeleteView,
    AppointmentDetailView,
    AppointmentListView,
    AppointmentUpdateView,
    CalendarDayView,
    CalendarView,
)

app_name = "appointments"

urlpatterns = [
    path("appointments/", AppointmentListView.as_view(), name="appointment_list"),
    path("appointments/new/", AppointmentCreateView.as_view(), name="appointment_create"),
    path("appointments/<int:pk>/", AppointmentDetailView.as_view(), name="appointment_detail"),
    path("appointments/<int:pk>/edit/", AppointmentUpdateView.as_view(), name="appointment_update"),
    path("appointments/<int:pk>/delete/", AppointmentDeleteView.as_view(), name="appointment_delete"),
    path("calendar/", CalendarView.as_view(), name="calendar"),
    path("calendar/day/<str:date_str>/", CalendarDayView.as_view(), name="calendar_day"),
]
