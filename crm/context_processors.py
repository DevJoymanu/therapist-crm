from .services import notifications_for


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    items = notifications_for(request.user)
    try:
        from .models import AppointmentRequest
        pending = AppointmentRequest.objects.filter(
            therapist=request.user,
            status=AppointmentRequest.Status.PENDING,
        ).count()
    except Exception:
        pending = 0
    return {
        "notifications": items,
        "notification_count": len(items),
        "pending_request_count": pending,
    }
