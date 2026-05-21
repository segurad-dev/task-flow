"""Настройка асинхронного подключения к PostgreSQL через SQLAlchemy 2.0.

Экспортирует:
- engine: асинхронный движок для прямых запросов и Alembic.
- Base: базовый класс для всех ORM-моделей.
- get_db: FastAPI-зависимость, предоставляющая сессию БД на запрос.

Почему async, а не sync SQLAlchemy?
FastAPI работает на ASGI (asyncio). Если использовать синхронный
SQLAlchemy, каждый запрос к БД заблокирует event loop и все остальные
HTTP-запросы будут ждать. Async-версия позволяет обрабатывать сотни
запросов одновременно в одном потоке.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# create_async_engine — создаёт пул соединений к PostgreSQL.
# echo=True — логирует все SQL-запросы в stdout (удобно для отладки,
# отключи в продакшене через переменную окружения).
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# async_sessionmaker — фабрика сессий.
# expire_on_commit=False: после commit объекты не "протухают"
# и их можно читать без дополнительного SELECT.
# Это важно, потому что FastAPI возвращает объект ПОСЛЕ commit.
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей проекта.

    Все модели (User, Project, Task) должны наследоваться от Base.
    Это нужно для:
    - Alembic: autogenerate сканирует подклассы Base для создания миграций
    - Base.metadata.create_all: создание таблиц в тестах
    """


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: предоставляет сессию БД с автокоммитом и откатом при ошибке.

    Как это работает с FastAPI:
    Функция — генератор (yield). FastAPI вызывает её при каждом запросе:
    1. Открывает сессию (async with AsyncSessionLocal())
    2. Передаёт сессию в обработчик эндпоинта через Depends(get_db)
    3. После завершения обработчика возобновляет генератор (код после yield)
    4. Если обработчик завершился успешно → commit()
    5. Если было исключение → rollback(), затем исключение пробрасывается дальше

    Использование в роутере:
        @router.get("/")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(MyModel))
            ...

    Yields:
        AsyncSession: активная сессия, привязанная к текущему запросу.
            Одна сессия = одна транзакция = один HTTP-запрос.

    Raises:
        Exception: любое исключение из обработчика пробрасывается после rollback.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # commit() нужен явно: SQLAlchemy не коммитит автоматически.
            # Все db.add(), db.delete() накапливаются и применяются здесь.
            await session.commit()
        except Exception:
            # Если в обработчике было исключение — откатываем все изменения.
            # Это гарантирует атомарность: либо всё применяется, либо ничего.
            await session.rollback()
            raise
