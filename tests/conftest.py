"""Общие фикстуры pytest для интеграционных тестов.

Фикстура (fixture) — это функция, которая подготавливает данные или ресурсы
для теста. pytest вызывает её автоматически, если тест запрашивает её по имени.

Здесь реализован паттерн "тестовая изоляция":
- Отдельная тестовая БД (taskflow_test) — не портим данные dev-БД
- Rollback после каждого теста — изменения одного теста не видны другому
- Переопределение зависимости get_db — API использует тестовую сессию

Иерархия фикстур (от медленных к быстрым):
  setup_database (session) → создаётся 1 раз за всю тестовую сессию
    db_session (function) → создаётся заново для каждого теста
      client (function) → HTTP-клиент с тестовой БД
        auth_client (function) → клиент с JWT-токеном
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

# Берём URL из переменной среды (для CI) или используем дефолтную (для локальной разработки).
# CI устанавливает DATABASE_URL в .github/workflows/ci.yml
TEST_DB_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow_test"
)
# Создаём отдельный движок для тестов — не используем движок из app/database.py
test_engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Создаёт схему БД перед всеми тестами и удаляет после.

    scope="session": фикстура создаётся один раз на весь запуск pytest.
    Это быстрее чем создавать/удалять таблицы для каждого теста.

    autouse=True: применяется автоматически ко всем тестам в сессии,
    не нужно явно передавать как аргумент.

    Base.metadata.create_all: создаёт все таблицы из ORM-моделей.
    Alembic для тестов не используем — нет смысла применять миграции,
    достаточно создать схему напрямую из моделей.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # тесты выполняются здесь
    async with test_engine.begin() as conn:
        # Удаляем все таблицы после окончания тестовой сессии
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Предоставляет сессию БД с откатом изменений после каждого теста.

    scope не указан → по умолчанию "function": новая сессия для каждого теста.

    Почему rollback, а не commit?
    Если бы мы делали commit, данные тестов накапливались бы в БД.
    test_register_success создаёт user "u@test.com", следующий тест тоже
    попытается создать — и упадёт с "Email уже зарегистрирован".
    rollback() откатывает все изменения → каждый тест начинает с чистой БД.
    """
    async with TestSession() as session:
        yield session
        # Откатываем всё что было сделано в этом тесте
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Предоставляет AsyncClient с переопределённой зависимостью get_db.

    Ключевой механизм: dependency_overrides.
    FastAPI позволяет заменить любую зависимость для тестов:
        app.dependency_overrides[get_db] = тестовая_функция

    Теперь когда роутер вызывает Depends(get_db), FastAPI вместо оригинальной
    get_db вызовет нашу lambda, которая возвращает тестовую сессию.
    Так все запросы API в тестах идут в тестовую БД, а не в dev-БД.

    ASGITransport(app=app): httpx использует ASGI интерфейс напрямую,
    без реального HTTP-сервера. Быстро и без сетевых задержек.
    """
    # lambda: (yield db_session) — генератор, совместимый с FastAPI dependency
    app.dependency_overrides[get_db] = lambda: (yield db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    # Очищаем переопределения после теста — важно чтобы не влияло на другие тесты
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    """Предоставляет AsyncClient с JWT-токеном аутентифицированного пользователя.

    Большинство эндпоинтов требуют авторизацию. Вместо того чтобы в каждом тесте
    регистрироваться и логиниться, auth_client делает это один раз.

    После получения токена он добавляется в client.headers["Authorization"].
    httpx будет прикладывать этот заголовок ко всем последующим запросам.
    Это имитирует поведение реального клиента с сохранённым токеном.
    """
    # Регистрируем тестового пользователя
    await client.post(
        "/auth/register",
        json={"email": "auto@test.com", "username": "auto", "password": "autopass"},
    )
    # Входим и получаем токен
    r = await client.post(
        "/auth/login", data={"username": "auto@test.com", "password": "autopass"}
    )
    # Добавляем токен в заголовки — все последующие запросы будут авторизованы
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client
