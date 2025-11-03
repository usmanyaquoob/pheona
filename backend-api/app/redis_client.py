# backend-api/app/redis_client.py
from __future__ import annotations

import os
import logging
import redis
from .config import settings

log = logging.getLogger("pheona.redis")

def _build_client_from_url(url: str) -> redis.Redis:
    """
    Build a Redis client directly from REDIS_URL.
    We do NOT pass ssl/ssl_context kwargs to avoid version mismatches.
    If you need TLS, use a rediss:// URL. If non-TLS, use redis://.
    """
    return redis.from_url(
        url,
        decode_responses=True,
        health_check_interval=15,
    )

def _build_client_from_parts() -> redis.Redis:
    """
    Fallback: build from host/port/username/password envs without TLS flags.
    If you need TLS, provide a rediss:// REDIS_URL instead of parts.
    """
    host = settings.REDIS_HOST
    port = settings.REDIS_PORT
    username = settings.REDIS_USERNAME or "default"
    password = settings.REDIS_PASSWORD

    if not (host and port and password):
        raise RuntimeError("Redis not configured: set REDIS_URL or REDIS_HOST/REDIS_PORT/REDIS_PASSWORD")

    return redis.Redis(
        host=host,
        port=int(port),
        username=username,
        password=password,
        decode_responses=True,
        health_check_interval=15,
        # IMPORTANT: no ssl/ssl_context kwargs here; match your DB by using proper URL if you need TLS
    )

def get_client() -> redis.Redis:
    """
    Returns a Redis client WITHOUT forcing a connection at import time.
    """
    if settings.REDIS_URL:
        return _build_client_from_url(settings.REDIS_URL)

    return _build_client_from_parts()

# Export a lazy client. Do not ping/connect here.
r = get_client()
