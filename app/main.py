"""Точка входа приложения Task Flow.

Создаёт экземпляр FastAPI и подключает все роутеры:
- auth: регистрация и вход, выдача JWT-токена
- projects: CRUD проектов
- tasks: CRUD задач с кэшированием и фоновыми уведомлениями
- analytics: статистика по проектам и пользователю

Почему роутеры подключаются здесь, а не в отдельном файле?
FastAPI рекомендует держать app в одном месте — это точка входа для
uvicorn (app.main:app). Роутеры разбиты по файлам для разделения
ответственности, но собираются в одно приложение здесь.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analytics, auth, projects, tasks

# title и version отображаются в Swagger UI (http://localhost:8000/docs)
app = FastAPI(title="Task Flow", version="1.0.0")

# Разрешаем запросы от фронтенда (localhost:3000).
# Без этого браузер блокирует cross-origin запросы к localhost:8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include_router добавляет все эндпоинты роутера в приложение.
# prefix из роутера (/auth, /tasks и т.д.) автоматически применяется.
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(analytics.router)


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса.

    Используется Docker healthcheck, load balancer и мониторингом.
    Не требует авторизации — должен отвечать даже при проблемах с БД.
    """
    return {"status": "ok"}
