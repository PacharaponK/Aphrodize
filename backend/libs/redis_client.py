from arq import create_pool
from arq.connections import RedisSettings

from backend.core.config import settings


def redis_settings() -> RedisSettings:
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
    )


async def get_arq_pool():
    return await create_pool(redis_settings())
