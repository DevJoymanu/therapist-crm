from django.urls import path

from .views import (
    PatientCreateView,
    PatientDeleteView,
    PatientDetailView,
    PatientListView,
    PatientUpdateView,
)

app_name = "patients"

urlpatterns = [
    path("patients/", PatientListView.as_view(), name="patient_list"),
    path("patients/new/", PatientCreateView.as_view(), name="patient_create"),
    path("patients/<int:pk>/", PatientDetailView.as_view(), name="patient_detail"),
    path("patients/<int:pk>/edit/", PatientUpdateView.as_view(), name="patient_update"),
    path("patients/<int:pk>/delete/", PatientDeleteView.as_view(), name="patient_delete"),
]
