from .services import notifications_for


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    items = notifications_for(request.user)
    return {
        "notifications": items,
        "notification_count": len(items),
    }
