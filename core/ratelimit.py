import hashlib

from django.core.cache import cache
from django.shortcuts import render


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _key(prefix: str, identifier: str) -> str:
    digest = hashlib.sha256(identifier.encode()).hexdigest()[:20]
    return f"rl:{prefix}:{digest}"


def is_rate_limited(request, prefix: str, max_hits: int, window_seconds: int, per_user: bool = False) -> bool:
    if per_user and request.user.is_authenticated:
        identifier = f"u:{request.user.pk}"
    else:
        identifier = f"ip:{get_client_ip(request)}"
    key = _key(prefix, identifier)
    if cache.add(key, 1, window_seconds):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window_seconds)
        return False
    return count > max_hits


def rate_limited_response(request):
    return render(request, "crm/rate_limited.html", status=429)
