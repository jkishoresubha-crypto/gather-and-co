import logging
import time

logger = logging.getLogger("gather.requests")


class RequestLoggingMiddleware:
    """Logs method, path, status and duration for every request.

    Only the path is logged – never query strings, bodies, cookies or headers –
    so secrets and personal data stay out of the logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            duration = (time.perf_counter() - start) * 1000
            logger.exception("request_failed method=%s path=%s duration_ms=%.1f",
                             request.method, request.path, duration)
            raise
        duration = (time.perf_counter() - start) * 1000
        level = logging.ERROR if response.status_code >= 500 else (
            logging.WARNING if response.status_code >= 400 else logging.INFO)
        logger.log(level, "request method=%s path=%s status=%s duration_ms=%.1f",
                   request.method, request.path, response.status_code, duration)
        return response

    def process_exception(self, request, exception):
        logger.error("unhandled_exception method=%s path=%s error=%s",
                     request.method, request.path, type(exception).__name__)
        return None


class HealthCheckMiddleware:
    """Answers /health/ before host validation and HTTPS redirects.

    The hosting provider's health checker may call the service on an internal
    address, which would otherwise be rejected by ALLOWED_HOSTS.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/" and request.method == "GET":
            from .views import health
            return health(request)
        return self.get_response(request)
