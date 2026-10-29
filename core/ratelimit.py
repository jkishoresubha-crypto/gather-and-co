"""A tiny fixed-window rate limiter backed by Django's cache.

Simple enough to explain: each client IP gets a counter per action that
expires after `window` seconds. Once the counter exceeds `limit`, requests
are refused with HTTP 429 until the window resets.
"""
from django.core.cache import cache


def client_ip(request):
    # Render (and most proxies) put the real client first in X-Forwarded-For.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(request, action, limit, window=60):
    key = f"rl:{action}:{client_ip(request)}"
    added = cache.add(key, 1, timeout=window)
    if added:
        return False
    try:
        count = cache.incr(key)
    except ValueError:  # key expired between add() and incr()
        cache.set(key, 1, timeout=window)
        return False
    return count > limit
