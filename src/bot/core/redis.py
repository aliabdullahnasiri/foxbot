from redis.asyncio import Redis

from bot.core.config import settings

redis = Redis.from_url(settings.REDIS_URL.get_secret_value(), decode_responses=True)
