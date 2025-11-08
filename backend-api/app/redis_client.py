# backend-api/app/redis_client.py
from __future__ import annotations
import os
import redis
from typing import Optional
from .config import settings

"""
Lazy Redis client that supports:
- REDIS_URL (redis://... or rediss://...)
- OR REDIS_HOST/REDIS_PORT/REDIS_PASSWORD (+ optional REDIS_TLS=1 to enable TLS)
No connection is attempted at import time.
"""

_client: Optional[redis.Redis] = None

def _bool_env(val: Optional[bool | str]) -> bool:
    if isinstance(val, bool):
        return val
    if not val:
        return False
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")

def get_client() -> redis.Redis:
    global _client
    if _client is not None:
        return _client

    if settings.REDIS_URL:
        # from_url will handle redis:// vs rediss:// automatically
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return _client

    if not (settings.REDIS_HOST and settings.REDIS_PORT and settings.REDIS_PASSWORD):
        raise RuntimeError(
            "Redis is not configured. Set REDIS_URL or REDIS_HOST/REDIS_PORT/REDIS_PASSWORD."
        )

    use_tls = _bool_env(settings.REDIS_TLS)
    _client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        username=settings.REDIS_USERNAME or "default",
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        ssl=use_tls,            # redis-py supports ssl=... for TLS connections
    )
    return _client

class _RedisProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)

# Export a proxy that lazily resolves the client
r = _RedisProxy()
