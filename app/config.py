"""Конфигурация приложения через переменные окружения.

Значения читаются из файла .env при локальной разработке
и из переменных среды в Docker/CI. Единственное место,
где определяются настройки — не читать os.environ напрямую.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения.

    Атрибуты:
        DATABASE_URL: строка подключения к PostgreSQL (asyncpg-формат).
        REDIS_URL: строка подключения к Redis.
        RABBITMQ_URL: строка подключения к RabbitMQ (AMQP-формат).
        SECRET_KEY: секрет для подписи JWT-токенов.
        ALGORITHM: алгоритм подписи JWT (по умолчанию HS256).
        ACCESS_TOKEN_EXPIRE_MINUTES: время жизни токена в минутах.
    """

    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
