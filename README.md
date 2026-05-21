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
git clone https://github.com/your-username/task-flow
cd task-flow
cp .env.example .env
docker-compose up --build
```

API: **http://localhost:8000/docs**
RabbitMQ UI: **http://localhost:15672** (guest / guest)

## API

| Метод | Эндпоинт | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Получить JWT токен |
| GET | `/tasks/` | Список задач (с кэшем Redis) |
| POST | `/tasks/` | Создать задачу |
| GET | `/tasks/{id}` | Получить задачу |
| PATCH | `/tasks/{id}` | Обновить задачу / статус |
| DELETE | `/tasks/{id}` | Удалить задачу |
| GET | `/projects/` | Список проектов |
| POST | `/projects/` | Создать проект |
| GET | `/analytics/project/{id}` | Статистика по проекту |
| GET | `/analytics/me` | Личная статистика |

## Примеры запросов

```bash
# Регистрация
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user", "password": "secret"}'

# Логин → получить токен
curl -X POST http://localhost:8000/auth/login \
  -d 'username=user@example.com&password=secret'

# Создать задачу (с токеном)
curl -X POST http://localhost:8000/tasks/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Написать тесты", "project_id": 1}'

# Фильтрация по статусу
curl http://localhost:8000/tasks/?status=in_progress \
  -H "Authorization: Bearer <token>"
```

## Тесты

```bash
pytest tests/ -v
```

## Миграции

```bash
alembic revision --autogenerate -m "описание"
alembic upgrade head
```

## Архитектура

- **Авторизация** — JWT Bearer токены, `passlib` bcrypt для паролей
- **Кэш** — список задач хранится в Redis (TTL 60с), инвалидируется при изменениях
- **Фоновые задачи** — Celery + RabbitMQ: уведомления при смене статуса, еженедельный отчёт по расписанию
- **Миграции** — Alembic с автогенерацией из SQLAlchemy-моделей
- **CI** — GitHub Actions: линтер ruff + pytest при каждом пуше
