"""
Redis-backed caching layer with graceful degradation.

If Redis is not available (not installed, not running, connection refused),
all cache operations silently return None / no-op so the pipeline still works
at full latency without crashing.
"""

import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CacheLayer:
    """Thin wrapper around Redis for JSON-serialisable cache entries."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis = None
        try:
            import redis as _redis_lib

            self._redis = _redis_lib.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Quick connectivity check – will raise if the server is down.
            self._redis.ping()
            logger.info("Redis cache connected at %s", redis_url)
        except Exception as exc:
            logger.warning(
                "Redis unavailable (%s). Caching is DISABLED – "
                "the API will work normally but without cache speed-ups.",
                exc,
            )
            self._redis = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._redis is not None

    @staticmethod
    def hash_key(text: str) -> str:
        """Deterministic SHA-256 hash of normalised input text."""
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Core get / set
    # ------------------------------------------------------------------

    def get(self, namespace: str, key: str) -> Optional[dict]:
        """Return cached dict or *None* on miss / error."""
        if not self._redis:
            return None
        try:
            raw = self._redis.get(f"{namespace}:{key}")
            if raw is not None:
                return json.loads(raw)
        except Exception as exc:
            logger.debug("Cache GET error (%s:%s): %s", namespace, key, exc)
        return None

    def set(self, namespace: str, key: str, value: dict, ttl: int = 3600) -> None:
        """Store *value* as JSON with a TTL (seconds). Fails silently."""
        if not self._redis:
            return
        try:
            self._redis.setex(
                f"{namespace}:{key}", ttl, json.dumps(value, ensure_ascii=False)
            )
        except Exception as exc:
            logger.debug("Cache SET error (%s:%s): %s", namespace, key, exc)
