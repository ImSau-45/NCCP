import redis
from backend.config import Config


class CacheService:
    def __init__(self):
        self.client = redis.from_url(Config.REDIS_URL)

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value, expire=Config.REDIS_CACHE_TTL):
        self.client.set(key, value, ex=expire)

    def delete(self, key):
        self.client.delete(key)
