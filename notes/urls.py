from django.urls import path

from .views import (
    CriterionCreateView,
    CriterionDeleteView,
    CriterionListView,
    CriterionUpdateView,
    SessionCreateView,
    SessionDeleteView,
    SessionDetailView,
    SessionListView,
    SessionUpdateView,
)

app_name = "notes"

urlpatterns = [
    path("sessions/", SessionListView.as_view(), name="session_list"),
    path("sessions/new/", SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:pk>/", SessionDetailView.as_view(), name="session_detail"),
    path("sessions/<int:pk>/edit/", SessionUpdateView.as_view(), name="session_update"),
    path("sessions/<int:pk>/delete/", SessionDeleteView.as_view(), name="session_delete"),
    path("criteria/", CriterionListView.as_view(), name="criterion_list"),
    path("criteria/new/", CriterionCreateView.as_view(), name="criterion_create"),
    path("criteria/<int:pk>/edit/", CriterionUpdateView.as_view(), name="criterion_update"),
    path("criteria/<int:pk>/delete/", CriterionDeleteView.as_view(), name="criterion_delete"),
]
