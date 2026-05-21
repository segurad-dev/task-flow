# Руководство для контрибьюторов

## Предварительные требования

| Инструмент | Версия | Зачем |
|---|---|---|
| Docker | 24+ | Запуск всех сервисов |
| Docker Compose | 2.x | Оркестрация контейнеров |
| Python | 3.11+ | Локальная разработка и тесты |
| Git | любая | Управление версиями |

---

## Локальный запуск

### Вариант 1 — через Docker (рекомендуется)

```bash
git clone https://github.com/segurad-dev/task-flow
cd task-flow
cp .env.example .env
# Заполнить SECRET_KEY в .env (минимум 32 символа)
docker-compose up --build
```

Сервисы запустятся автоматически. После этого:
- API: http://localhost:8000/docs
- RabbitMQ UI: http://localhost:15672 (guest/guest)

### Вариант 2 — локально без Docker

Подходит для активной разработки (без пересборки контейнера при каждом изменении).

```bash
# Создать и активировать виртуальное окружение
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить PostgreSQL, Redis, RabbitMQ через Docker
docker-compose up db redis rabbitmq -d

# Применить миграции
alembic upgrade head

# Запустить приложение
uvicorn app.main:app --reload
```

---

## Запуск тестов

Тесты используют отдельную тестовую базу данных (`taskflow_test`).

```bash
# Создать тестовую БД (если не создана)
docker-compose exec db psql -U postgres -c "CREATE DATABASE taskflow_test;"

# Запустить все тесты
pytest tests/ -v

# Запустить конкретный файл
pytest tests/test_tasks.py -v

# Запустить по имени теста
pytest -k "test_create" -v

# Показать только упавшие
pytest tests/ --tb=short
```

---

## Стиль кода

Проект использует [ruff](https://docs.astral.sh/ruff/) для линтинга и форматирования.

```bash
# Проверить весь код
ruff check app/

# Автоматически исправить
ruff check app/ --fix
```

**Правила:**
- Максимальная длина строки: 100 символов
- Цель Python: 3.11
- Активные правила: E (pycodestyle), F (pyflakes), I (isort)
- Порядок импортов: стандартная библиотека → сторонние пакеты → локальные
- Type hints обязательны для всех функций
- Docstring обязателен для всех модулей, классов и функций

---

## Добавление новой функциональности

Стандартный маршрут для новой фичи:

### 1. Модель (если нужна новая таблица)

```python
# app/models/my_model.py
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column

class MyModel(Base):
    __tablename__ = "my_models"
    id: Mapped[int] = mapped_column(primary_key=True)
    ...
```

Добавить в `app/models/__init__.py`.

### 2. Миграция

```bash
alembic revision --autogenerate -m "add my_model table"
# Проверить сгенерированный файл в alembic/versions/
alembic upgrade head
```

### 3. Pydantic-схемы

```python
# app/schemas/my_model.py
from pydantic import BaseModel

class MyModelCreate(BaseModel): ...
class MyModelRead(BaseModel):
    model_config = {"from_attributes": True}
```

Добавить в `app/schemas/__init__.py`.

### 4. Роутер

```python
# app/routers/my_router.py
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/my-resource", tags=["my-resource"])

@router.get("/")
async def list_items(...): ...
```

Подключить в `app/main.py`:
```python
from app.routers import my_router
app.include_router(my_router.router)
```

### 5. Тесты

```python
# tests/test_my_router.py
import pytest

@pytest.mark.asyncio
async def test_create_item(auth_client):
    """Описание: что проверяет тест."""
    r = await auth_client.post("/my-resource/", json={...})
    assert r.status_code == 201
```

---

## Работа с миграциями

```bash
# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "краткое описание"

# ВАЖНО: проверить сгенерированный файл в alembic/versions/
# Autogenerate не всегда корректно определяет все изменения

# Применить миграции
alembic upgrade head

# Посмотреть текущую версию
alembic current

# Откатить последнюю миграцию
alembic downgrade -1

# Откатить все миграции (только для dev!)
alembic downgrade base
```

---

## Процесс создания Pull Request

1. Создать ветку от `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. Реализовать изменения с тестами

3. Убедиться что тесты проходят:
   ```bash
   pytest tests/ -v
   ```

4. Проверить линтер:
   ```bash
   ruff check app/
   ```

5. Создать PR в `main` с описанием:
   - Что сделано и зачем
   - Как протестировать
   - Какие файлы изменены

CI автоматически запустит ruff и pytest при открытии PR.
