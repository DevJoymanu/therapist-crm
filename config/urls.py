from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import RateLimitedLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", RateLimitedLoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("core.urls")),
    path("", include("patients.urls")),
    path("", include("appointments.urls")),
    path("", include("notes.urls")),
    path("", include("booking.urls")),
]
