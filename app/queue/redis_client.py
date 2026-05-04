from redis import Redis

from app.core.settings import settings


def get_redis_connection() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)