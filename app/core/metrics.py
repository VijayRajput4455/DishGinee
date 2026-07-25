from typing import Any

from fastapi import Request, Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    # Request metrics
    REQUEST_COUNT = Counter(
        "dishgenie_requests_total",
        "Total number of HTTP requests processed",
        ["method", "endpoint", "status_code"],
    )

    REQUEST_LATENCY = Histogram(
        "dishgenie_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
    )

    # Business & Queue metrics
    TASK_REQUESTS = Counter(
        "dishgenie_task_requests_total",
        "Total background worker task requests published",
        ["task_type", "status"],
    )

    RATE_LIMIT_EXCEEDED = Counter(
        "dishgenie_rate_limit_exceeded_total",
        "Total rate limit violations",
        ["endpoint", "client_ip"],
    )

    ACTIVE_CONNECTIONS = Gauge(
        "dishgenie_active_connections",
        "Number of active HTTP connections",
    )

    CACHE_HITS = Counter(
        "dishgenie_cache_hits_total",
        "Total Redis cache hits",
    )

    CACHE_MISSES = Counter(
        "dishgenie_cache_misses_total",
        "Total Redis cache misses",
    )


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics scrape endpoint for monitoring dashboards."""
    if not PROMETHEUS_AVAILABLE:
        return Response(
            content="# prometheus_client library not installed\n",
            media_type="text/plain",
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def track_requests(request: Request, response: Any, process_time: float) -> None:
    """Middleware tracker for HTTP request count and latency metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    endpoint = request.url.path
    status_code = str(getattr(response, "status_code", 500))

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint,
    ).observe(process_time)


def increment_cache_metrics(hit: bool) -> None:
    """Track cache performance metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    if hit:
        CACHE_HITS.inc()
    else:
        CACHE_MISSES.inc()


def increment_rate_limit_metric(endpoint: str, client_ip: str) -> None:
    """Track rate limit violations."""
    if not PROMETHEUS_AVAILABLE:
        return
    RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint, client_ip=client_ip).inc()
