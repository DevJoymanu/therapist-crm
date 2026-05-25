from django.urls import path

from .views import (
    ApproveRequestView,
    BookingCheckView,
    BookingConfirmView,
    BookingNewClientView,
    BookingPortalView,
    BookingRequestsView,
    BookingReturningView,
    ConsentDoneView,
    ConsentFormView,
    DashboardSendBookingLinkView,
    DeclineRequestView,
    GenerateLinkView,
    PersonalizedBookingView,
    SharedLinkView,
    WhatsAppBookingLinkView,
)

app_name = "booking"

urlpatterns = [
    path("consent/<uuid:token>/", ConsentFormView.as_view(), name="consent_form"),
    path("consent/<uuid:token>/done/", ConsentDoneView.as_view(), name="consent_done"),
    path("book/<str:username>/", BookingPortalView.as_view(), name="booking_portal"),
    path("book/<str:username>/check/", BookingCheckView.as_view(), name="booking_check"),
    path("book/<str:username>/returning/<int:patient_pk>/", BookingReturningView.as_view(), name="booking_returning"),
    path("book/<str:username>/new/", BookingNewClientView.as_view(), name="booking_new_client"),
    path("book/p/<uuid:token>/", PersonalizedBookingView.as_view(), name="booking_personal"),
    path("book/confirm/<uuid:token>/", BookingConfirmView.as_view(), name="booking_confirm"),
    path("dashboard/send-booking-link/", DashboardSendBookingLinkView.as_view(), name="dashboard_send_booking_link"),
    path("booking/", BookingRequestsView.as_view(), name="booking_requests"),
    path("booking/<int:pk>/approve/", ApproveRequestView.as_view(), name="request_approve"),
    path("booking/<int:pk>/decline/", DeclineRequestView.as_view(), name="request_decline"),
    path("link/<uuid:token>/", SharedLinkView.as_view(), name="shared_link"),
    path("patients/<int:pk>/links/<str:link_type>/", GenerateLinkView.as_view(), name="generate_link"),
    path("patients/<int:pk>/whatsapp/", WhatsAppBookingLinkView.as_view(), name="whatsapp_booking"),
]
