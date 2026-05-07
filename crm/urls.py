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
    path("sessions/", views.SessionListView.as_view(), name="session_list"),
    path("sessions/new/", views.SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view(), name="session_detail"),
    path("sessions/<int:pk>/edit/", views.SessionUpdateView.as_view(), name="session_update"),
    path("sessions/<int:pk>/delete/", views.SessionDeleteView.as_view(), name="session_delete"),
    path("criteria/", views.CriterionListView.as_view(), name="criterion_list"),
    path("criteria/new/", views.CriterionCreateView.as_view(), name="criterion_create"),
    path("criteria/<int:pk>/edit/", views.CriterionUpdateView.as_view(), name="criterion_update"),
    path("criteria/<int:pk>/delete/", views.CriterionDeleteView.as_view(), name="criterion_delete"),
]
