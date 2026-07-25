import json
import threading
from typing import Any

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Thread-safe singleton Redis caching client with graceful offline fallback."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "RedisCache":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._client: Any = None
        self._lock = threading.Lock()
        self._initialized = True

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        with self._lock:
            if self._client is not None:
                return self._client

            try:
                from redis import Redis

                client = Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=1,
                    socket_connect_timeout=1,
                )
                client.ping()
                self._client = client
                logger.info(
                    "Redis cache connected | host=%s port=%s db=%s",
                    settings.REDIS_HOST,
                    settings.REDIS_PORT,
                    settings.REDIS_DB,
                )
            except Exception as exc:
                logger.info("Redis cache unavailable (%s); operating in DB-only mode", exc)
                self._client = None

        return self._client

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        """Retrieve JSON payload from Redis by key."""
        client = self._get_client()
        if client is None:
            return None

        try:
            raw = client.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as err:
            logger.warning("Redis get_json failed | key=%s err=%s", key, err)
            return None

    def set_json(
        self, key: str, value: dict[str, Any] | list[Any], ttl_seconds: int | None = None
    ) -> None:
        """Store JSON payload in Redis with TTL expiration."""
        client = self._get_client()
        if client is None:
            return

        ttl = ttl_seconds if ttl_seconds is not None else settings.REDIS_DEFAULT_TTL_SECONDS
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as err:
            logger.warning("Redis set_json failed | key=%s err=%s", key, err)

    def delete(self, key: str) -> None:
        """Remove a cached key from Redis."""
        client = self._get_client()
        if client is None:
            return

        try:
            client.delete(key)
        except Exception as err:
            logger.warning("Redis delete failed | key=%s err=%s", key, err)

    def check_rate_limit(self, key: str, limit: int) -> bool:
        """Check if rate limit counter has been exceeded. Returns True if within limit, False if exceeded."""
        client = self._get_client()
        if client is None:
            return True  # Allow request if Redis is offline

        try:
            current_count = client.get(key)
            if current_count is None:
                return True
            return int(current_count) < limit
        except Exception as err:
            logger.warning("Redis rate limit check failed | key=%s err=%s", key, err)
            return True

    def increment_rate_limit(self, key: str, window_seconds: int) -> None:
        """Increment rate limit counter for key and set window TTL."""
        client = self._get_client()
        if client is None:
            return

        try:
            current = client.incr(key)
            if current == 1:
                client.expire(key, window_seconds)
        except Exception as err:
            logger.warning("Redis rate limit increment failed | key=%s err=%s", key, err)


_redis_cache = RedisCache()


def get_redis_cache() -> RedisCache:
    """Factory function returning thread-safe RedisCache instance."""
    return _redis_cache
