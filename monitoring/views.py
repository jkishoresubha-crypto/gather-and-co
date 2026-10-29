import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from assistant import mongo

logger = logging.getLogger("gather.health")


@never_cache
@require_GET
def health(request):
    """Machine-readable health check.

    - `status`: "ok" if the app can serve core pages (PostgreSQL reachable),
      otherwise "error" with HTTP 503.
    - `checks.mongodb`: optional dependency – chat logging degrades gracefully,
      so a MongoDB outage is reported as "degraded" but still returns 200.
    """
    checks = {"app": "ok"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except DatabaseError as exc:
        logger.error("Health check: database unavailable (%s)", type(exc).__name__)
        checks["database"] = "unavailable"

    mongo_state = mongo.ping()
    checks["mongodb"] = {True: "ok", False: "unavailable", None: "not_configured"}[mongo_state]

    if checks["database"] != "ok":
        status, code = "error", 503
    elif checks["mongodb"] == "unavailable":
        status, code = "degraded", 200
    else:
        status, code = "ok", 200
    return JsonResponse({"status": status, "checks": checks}, status=code)
