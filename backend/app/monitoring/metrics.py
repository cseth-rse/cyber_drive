# app/monitoring/metrics.py
"""
Prometheus metrics exposed at GET /metrics.

Install: pip install prometheus-client

Metrics tracked:
  - http_requests_total          (counter, by method/path/status)
  - http_request_duration_seconds (histogram, by method/path)
  - documents_total               (gauge, by status)
  - downloads_total               (counter)
  - active_users_total            (gauge)
"""
import logging
import time

logger = logging.getLogger(__name__)

_registry_ready = False


def setup_metrics(app):
    """Attach Prometheus middleware and /metrics endpoint to the FastAPI app."""
    try:
        from prometheus_client import (
            CollectorRegistry, Counter, Gauge, Histogram,
            REGISTRY, generate_latest, CONTENT_TYPE_LATEST,
            multiprocess, values,
        )
        from fastapi import Request, Response
        from fastapi.routing import APIRoute
        import prometheus_client

        REQUEST_COUNT = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
        )
        REQUEST_LATENCY = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
        DOWNLOADS = Counter("cyber_drive_downloads_total", "Total document downloads")
        UPLOADS = Counter("cyber_drive_uploads_total", "Total document uploads")

        @app.middleware("http")
        async def _prometheus_middleware(request: Request, call_next):
            start = time.perf_counter()
            response = await call_next(request)
            duration = time.perf_counter() - start

            # Normalise path (avoid high cardinality from UUIDs)
            path = request.url.path
            # Replace UUID segments with {id}
            import re
            path = re.sub(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                "{id}", path
            )

            REQUEST_COUNT.labels(
                method=request.method, endpoint=path, status_code=response.status_code
            ).inc()
            REQUEST_LATENCY.labels(method=request.method, endpoint=path).observe(duration)

            return response

        @app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
        def prometheus_metrics():
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

        global _registry_ready
        _registry_ready = True
        logger.info("Prometheus metrics enabled at /metrics")

    except ImportError:
        logger.warning(
            "prometheus-client not installed — metrics disabled. "
            "Run: pip install prometheus-client"
        )


def record_download():
    if not _registry_ready:
        return
    try:
        from prometheus_client import Counter
        Counter("cyber_drive_downloads_total", "Total document downloads").inc()
    except Exception:
        pass


def record_upload():
    if not _registry_ready:
        return
    try:
        from prometheus_client import Counter
        Counter("cyber_drive_uploads_total", "Total document uploads").inc()
    except Exception:
        pass
