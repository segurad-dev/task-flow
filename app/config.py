"""Конфигурация приложения через переменные окружения.

Значения читаются из файла .env при локальной разработке
и из переменных среды в Docker/CI. Единственное место,
где определяются настройки — не читать os.environ напрямую.

Почему pydantic-settings, а не python-dotenv?
- Автоматическая валидация типов (int, str)
- Понятные ошибки при отсутствии обязательных переменных
- Встроенная поддержка .env файлов
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения.

    Pydantic-settings при старте приложения:
    1. Читает файл .env (если указан в Config.env_file)
    2. Проверяет переменные окружения системы (приоритет выше .env)
    3. Валидирует типы — int, str, bool и т.д.
    4. Бросает ValidationError с понятным сообщением если поле отсутствует

    Атрибуты:
        DATABASE_URL: строка подключения к PostgreSQL в asyncpg-формате.
            Формат: postgresql+asyncpg://user:password@host:port/dbname
            Драйвер asyncpg требует async-префикс для работы с asyncio.
        REDIS_URL: строка подключения к Redis.
            Формат: redis://host:port/db_index
        RABBITMQ_URL: строка подключения к RabbitMQ в AMQP-формате.
            Формат: amqp://user:password@host:port/vhost
        SECRET_KEY: секрет для подписи JWT-токенов.
            Должен быть случайным и длиной минимум 32 символа.
            Генерация: openssl rand -hex 32
        ALGORITHM: алгоритм подписи JWT. HS256 — HMAC с SHA-256.
            Симметричный: один ключ для подписи и верификации.
        ACCESS_TOKEN_EXPIRE_MINUTES: время жизни токена в минутах.
            После истечения клиент получит 401 и должен войти снова.
    """

    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        # Указываем pydantic-settings где искать .env файл
        # Если файла нет — используются переменные среды (для Docker/CI)
        env_file = ".env"
        # Игнорируем неизвестные переменные (например TEST_DATABASE_URL)
        extra = "ignore"


# Единственный экземпляр настроек для всего приложения.
# Импортируй settings, а не класс Settings напрямую.
settings = Settings()
