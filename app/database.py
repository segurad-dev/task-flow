"""Настройка асинхронного подключения к PostgreSQL через SQLAlchemy 2.0.

Экспортирует:
- engine: асинхронный движок для прямых запросов и Alembic.
- Base: базовый класс для всех ORM-моделей.
- get_db: FastAPI-зависимость, предоставляющая сессию БД на запрос.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей проекта."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: предоставляет сессию БД с автокоммитом и откатом при ошибке.

    Yields:
        AsyncSession: активная сессия, привязанная к текущему запросу.

    Raises:
        Exception: любое исключение из обработчика пробрасывается после rollback.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
