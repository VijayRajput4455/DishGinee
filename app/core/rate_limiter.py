import time
from typing import Callable

from fastapi import HTTPException, Request, Response, status

from app.core.config import settings
from app.core.logger import get_logger
from app.core.metrics import increment_rate_limit_metric
from app.services.redis_cache import get_redis_cache

logger = get_logger(__name__)

# Fallback in-memory rate limit store: client_ip -> list of timestamp floats
_memory_rate_limit_store: dict[str, list[float]] = {}


def check_ip_rate_limit(client_ip: str, endpoint: str) -> bool:
    """Check and increment IP rate limit counter. Returns True if allowed, False if limit exceeded."""
    limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    key = f"rate_limit:{client_ip}:{endpoint}"

    redis_cache = get_redis_cache()
    if redis_cache._get_client() is not None:
        within_limit = redis_cache.check_rate_limit(key, limit)
        if not within_limit:
            increment_rate_limit_metric(endpoint, client_ip)
            return False
        redis_cache.increment_rate_limit(key, window)
        return True

    # Fallback in-memory rate limiting when Redis is offline
    now = time.time()
    timestamps = _memory_rate_limit_store.get(key, [])
    # Remove timestamps older than window
    valid_timestamps = [ts for ts in timestamps if now - ts < window]

    if len(valid_timestamps) >= limit:
        increment_rate_limit_metric(endpoint, client_ip)
        _memory_rate_limit_store[key] = valid_timestamps
        return False

    valid_timestamps.append(now)
    _memory_rate_limit_store[key] = valid_timestamps
    return True


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """HTTP middleware checking request rate limits for API endpoints."""
    # Skip rate limiting for static files, docs, health, metrics, and worker status endpoints
    path = request.url.path
    if (
        path.startswith("/static")
        or path in ["/docs", "/redoc", "/openapi.json", "/health", "/metrics", "/worker-status"]
    ):
        return await call_next(request)

    client_ip = request.client.host if request.client else "127.0.0.1"
    if not check_ip_rate_limit(client_ip, path):
        logger.warning("Rate limit exceeded for client IP %s on %s", client_ip, path)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before making more requests.",
        )

    return await call_next(request)
