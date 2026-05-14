from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("patients/", views.PatientListView.as_view(), name="patient_list"),
    path("patients/new/", views.PatientCreateView.as_view(), name="patient_create"),
    path("patients/<int:pk>/", views.PatientDetailView.as_view(), name="patient_detail"),
    path("patients/<int:pk>/edit/", views.PatientUpdateView.as_view(), name="patient_update"),
    path("patients/<int:pk>/delete/", views.PatientDeleteView.as_view(), name="patient_delete"),
    path("appointments/", views.AppointmentListView.as_view(), name="appointment_list"),
    path("appointments/new/", views.AppointmentCreateView.as_view(), name="appointment_create"),
    path("appointments/<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment_detail"),
    path("appointments/<int:pk>/edit/", views.AppointmentUpdateView.as_view(), name="appointment_update"),
    path("appointments/<int:pk>/delete/", views.AppointmentDeleteView.as_view(), name="appointment_delete"),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    path("calendar/day/<str:date_str>/", views.CalendarDayView.as_view(), name="calendar_day"),
    path("sessions/", views.SessionListView.as_view(), name="session_list"),
    path("sessions/new/", views.SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view(), name="session_detail"),
    path("sessions/<int:pk>/edit/", views.SessionUpdateView.as_view(), name="session_update"),
    path("sessions/<int:pk>/delete/", views.SessionDeleteView.as_view(), name="session_delete"),
    path("criteria/", views.CriterionListView.as_view(), name="criterion_list"),
    path("criteria/new/", views.CriterionCreateView.as_view(), name="criterion_create"),
    path("criteria/<int:pk>/edit/", views.CriterionUpdateView.as_view(), name="criterion_update"),
    path("criteria/<int:pk>/delete/", views.CriterionDeleteView.as_view(), name="criterion_delete"),
    path("consent/<uuid:token>/", views.ConsentFormView.as_view(), name="consent_form"),
    path("consent/<uuid:token>/done/", views.ConsentDoneView.as_view(), name="consent_done"),
    # Public booking portal
    path("book/<str:username>/", views.BookingPortalView.as_view(), name="booking_portal"),
    path("book/<str:username>/check/", views.BookingCheckView.as_view(), name="booking_check"),
    path("book/<str:username>/returning/<int:patient_pk>/", views.BookingReturningView.as_view(), name="booking_returning"),
    path("book/<str:username>/new/", views.BookingNewClientView.as_view(), name="booking_new_client"),
    path("book/p/<uuid:token>/", views.PersonalizedBookingView.as_view(), name="booking_personal"),
    path("book/confirm/<uuid:token>/", views.BookingConfirmView.as_view(), name="booking_confirm"),
    # Dashboard send-link
    path("dashboard/send-booking-link/", views.DashboardSendBookingLinkView.as_view(), name="dashboard_send_booking_link"),
    # Therapist booking management
    path("booking/", views.BookingRequestsView.as_view(), name="booking_requests"),
    path("booking/<int:pk>/approve/", views.ApproveRequestView.as_view(), name="request_approve"),
    path("booking/<int:pk>/decline/", views.DeclineRequestView.as_view(), name="request_decline"),
    # Expiring shareable links
    path("link/<uuid:token>/", views.SharedLinkView.as_view(), name="shared_link"),
    path("patients/<int:pk>/links/<str:link_type>/", views.GenerateLinkView.as_view(), name="generate_link"),
    # WhatsApp booking link
    path("patients/<int:pk>/whatsapp/", views.WhatsAppBookingLinkView.as_view(), name="whatsapp_booking"),
]
