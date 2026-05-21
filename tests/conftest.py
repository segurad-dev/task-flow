"""Общие фикстуры pytest для интеграционных тестов.

Создаёт изолированную тестовую БД, переопределяет зависимость get_db,
предоставляет HTTP-клиент и аутентифицированный клиент для тестов.
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow_test"
)
test_engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Создаёт схему БД перед всеми тестами и удаляет после.

    scope="session" — выполняется один раз за всю тестовую сессию.
    autouse=True — применяется автоматически без явного указания в тестах.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Предоставляет сессию БД с откатом изменений после каждого теста.

    rollback() гарантирует изоляцию тестов: данные одного теста
    не влияют на следующий.
    """
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Предоставляет AsyncClient с переопределённой зависимостью get_db.

    dependency_overrides подменяет get_db тестовой сессией,
    так что все запросы к API идут в тестовую БД.
    """
    app.dependency_overrides[get_db] = lambda: (yield db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    """Предоставляет AsyncClient с JWT-токеном аутентифицированного пользователя.

    Регистрирует тестового пользователя, выполняет вход и добавляет
    заголовок Authorization ко всем последующим запросам клиента.
    """
    await client.post(
        "/auth/register",
        json={"email": "auto@test.com", "username": "auto", "password": "autopass"},
    )
    r = await client.post(
        "/auth/login", data={"username": "auto@test.com", "password": "autopass"}
    )
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client
