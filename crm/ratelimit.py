"""
Rate limiting utilities using Django's cache backend.

Uses a "fixed window" counter per IP (or per user for authenticated requests).
cache.add() is atomic on both LocMemCache and Redis/Memcached, so there is no
meaningful race condition for this use-case.
"""
import hashlib

from django.core.cache import cache
from django.shortcuts import render


def get_client_ip(request):
    """Return the real client IP, respecting common reverse-proxy headers."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        # Take the leftmost (client) address; strip any whitespace
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _key(prefix: str, identifier: str) -> str:
    digest = hashlib.sha256(identifier.encode()).hexdigest()[:20]
    return f"rl:{prefix}:{digest}"


def is_rate_limited(
    request,
    prefix: str,
    max_hits: int,
    window_seconds: int,
    per_user: bool = False,
) -> bool:
    """
    Return True if the caller has exceeded max_hits in the current window.
    Increments the counter on every call regardless.

    Uses per-user counting when per_user=True and the request is authenticated;
    falls back to IP-based counting otherwise.
    """
    if per_user and request.user.is_authenticated:
        identifier = f"u:{request.user.pk}"
    else:
        identifier = f"ip:{get_client_ip(request)}"

    key = _key(prefix, identifier)

    # cache.add sets the key to 1 with the timeout only if it does not exist.
    # Returns True on success (key was new), False if key already existed.
    if cache.add(key, 1, window_seconds):
        return False  # First hit in this window — never limited

    try:
        count = cache.incr(key)
    except ValueError:
        # Key expired between add() and incr() — treat as first hit
        cache.set(key, 1, window_seconds)
        return False

    return count > max_hits


def rate_limited_response(request):
    """Return a 429 Too Many Requests response."""
    return render(request, "crm/rate_limited.html", status=429)
