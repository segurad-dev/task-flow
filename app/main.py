"""Точка входа приложения Task Flow.

Создаёт экземпляр FastAPI и подключает все роутеры:
- auth: регистрация и вход, выдача JWT-токена
- projects: CRUD проектов
- tasks: CRUD задач с кэшированием и фоновыми уведомлениями
- analytics: статистика по проектам и пользователю
"""

from fastapi import FastAPI

from app.routers import analytics, auth, projects, tasks

app = FastAPI(title="Task Flow", version="1.0.0")

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(analytics.router)


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}
