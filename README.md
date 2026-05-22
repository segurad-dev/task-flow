# Task Flow

REST API система управления задачами — портфолио-проект на Python.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)
![Docker](https://img.shields.io/badge/Docker-compose-blue?logo=docker)

## Стек

FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Redis · Celery · RabbitMQ · JWT · pytest · Docker · GitHub Actions

## Быстрый старт

```bash
git clone https://github.com/segurad-dev/task-flow
cd task-flow
cp .env.example .env
docker-compose up --build
```

API: **http://localhost:8000/docs**
RabbitMQ UI: **http://localhost:15672** (guest / guest)

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните значения:

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | Строка подключения к PostgreSQL (asyncpg) | `postgresql+asyncpg://postgres:postgres@db:5432/taskflow` |
| `REDIS_URL` | Строка подключения к Redis | `redis://redis:6379/0` |
| `RABBITMQ_URL` | Строка подключения к RabbitMQ (AMQP) | `amqp://guest:guest@rabbitmq:5672/` |
| `SECRET_KEY` | Секрет для подписи JWT-токенов (мин. 32 символа) | `openssl rand -hex 32` |
| `ALGORITHM` | Алгоритм подписи JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена в минутах | `30` |

> Никогда не коммитьте файл `.env` — он добавлен в `.gitignore`.

## API

| Метод | Эндпоинт | Авторизация | Описание |
|---|---|---|---|
| POST | `/auth/register` | — | Регистрация |
| POST | `/auth/login` | — | Получить JWT-токен |
| GET | `/tasks/` | Bearer | Список задач (с кэшем Redis) |
| POST | `/tasks/` | Bearer | Создать задачу |
| GET | `/tasks/{id}` | Bearer | Получить задачу |
| PATCH | `/tasks/{id}` | Bearer | Обновить задачу / статус |
| DELETE | `/tasks/{id}` | Bearer | Удалить задачу |
| GET | `/projects/` | Bearer | Список проектов |
| POST | `/projects/` | Bearer | Создать проект |
| GET | `/analytics/project/{id}` | Bearer | Статистика по проекту |
| GET | `/analytics/me` | Bearer | Личная статистика |

## Полный пример работы

Полный workflow от регистрации до получения аналитики:

```bash
# 1. Регистрация
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user", "password": "secret"}'

# 2. Логин → получить токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d 'username=user@example.com&password=secret' | jq -r '.access_token')

# 3. Создать проект
PROJECT_ID=$(curl -s -X POST http://localhost:8000/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Мой проект"}' | jq -r '.id')

# 4. Создать задачу
TASK_ID=$(curl -s -X POST http://localhost:8000/tasks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Написать тесты\", \"project_id\": $PROJECT_ID}" | jq -r '.id')

# 5. Обновить статус (триггерит Celery-уведомление)
curl -X PATCH http://localhost:8000/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'

# 6. Получить аналитику по проекту
curl http://localhost:8000/analytics/project/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN"

# 7. Фильтрация по статусу
curl "http://localhost:8000/tasks/?status=in_progress" \
  -H "Authorization: Bearer $TOKEN"
```

## Frontend Demo

Простой SPA-интерфейс для наглядной демонстрации API — без сборки, только CDN.

**Стек**: HTML + Alpine.js + Tailwind CSS

```bash
# Бэкенд уже запущен (docker-compose up)
cd frontend
python -m http.server 3000
# Открыть http://localhost:3000
```

Подробнее: [frontend/README.md](frontend/README.md)

## Как это работает

```
Клиент
  │
  ▼
FastAPI (роутер)
  │
  ├── JWT-токен → get_current_user → проверка в PostgreSQL
  │
  ├── GET /tasks/ → Redis (кэш) → PostgreSQL (если нет кэша)
  │
  ├── POST/PATCH/DELETE /tasks/ → PostgreSQL → инвалидация Redis
  │                                    └── Celery → RabbitMQ → Worker (уведомление)
  │
  └── GET /analytics/ → PostgreSQL (SQL-агрегации)
```

## Тесты

```bash
pytest tests/ -v           # все тесты
pytest tests/test_tasks.py # один файл
pytest -k "test_create" -v # по имени теста
```

## Миграции

```bash
# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "описание изменений"

# Применить все pending-миграции
alembic upgrade head

# Откатить одну миграцию
alembic downgrade -1
```

## Архитектура

Подробное описание архитектурных решений — в [ARCHITECTURE.md](ARCHITECTURE.md).

- **Авторизация** — JWT Bearer-токены, `passlib` bcrypt для паролей
- **Кэш** — список задач хранится в Redis (TTL 60с), инвалидируется при изменениях
- **Фоновые задачи** — Celery + RabbitMQ: уведомления при смене статуса, еженедельный отчёт по расписанию
- **Миграции** — Alembic с автогенерацией из SQLAlchemy-моделей
- **CI** — GitHub Actions: линтер ruff + pytest при каждом пуше

## Устранение неполадок

**Порт 5432 занят**
```bash
# Проверить что занимает порт
netstat -ano | findstr :5432   # Windows
lsof -i :5432                  # Linux/Mac
# Остановить локальный PostgreSQL или изменить порт в docker-compose.yml
```

**Redis недоступен / ошибки кэша**
```bash
docker-compose exec redis redis-cli ping  # должно вернуть PONG
docker-compose logs redis                 # смотреть логи
```

**Celery Worker не запускается**
```bash
docker-compose logs celery_worker
# Убедиться что RabbitMQ запущен: docker-compose ps rabbitmq
```

**Ошибки Alembic при миграции**
```bash
# Проверить текущую версию
alembic current
# Сбросить и пересоздать (только на dev-окружении!)
alembic downgrade base
alembic upgrade head
```

**Тесты падают с ошибкой подключения к БД**
```bash
# Убедиться что тестовая БД создана
docker-compose exec db psql -U postgres -c "CREATE DATABASE taskflow_test;"
# Или передать свой DATABASE_URL:
DATABASE_URL=postgresql+asyncpg://... pytest tests/ -v
```

**Контейнеры не запускаются после изменения кода**
```bash
docker-compose down && docker-compose up --build
```
