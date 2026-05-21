"""Клиент Redis для кэширования данных приложения.

Используется для кэша списка задач с TTL 60 секунд.
Ключ кэша: tasks:{user_id}.
"""

import redis.asyncio as aioredis

from app.config import settings

# decode_responses=True: Redis возвращает str вместо bytes
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
