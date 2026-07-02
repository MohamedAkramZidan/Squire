import logging
from typing import Optional

import redis

from config.settings import settings

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


def init_redis() -> None:
    global _pool, _client
    _pool = redis.ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    _client = redis.Redis(connection_pool=_pool)
    try:
        _client.ping()
        logger.info("Redis connected: %s", settings.redis_url)
    except redis.ConnectionError:
        logger.warning(
            "Redis unavailable at %s — state layer will operate in stateless mode.",
            settings.redis_url,
        )


def get_redis() -> Optional[redis.Redis]:
    if _client is None:
        return None
    try:
        _client.ping()
        return _client
    except (redis.ConnectionError, redis.TimeoutError):
        return None


def close_redis() -> None:
    global _pool, _client
    if _client:
        _client.close()
        _client = None
    if _pool:
        _pool.disconnect()
        _pool = None
