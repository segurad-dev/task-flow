"""Celery-приложение: конфигурация, задачи и расписание.

Broker: RabbitMQ — обеспечивает надёжную доставку сообщений между сервисами.
Backend: Redis — хранит результаты выполнения задач.

Задачи:
- send_notification: вызывается при смене статуса задачи.
- generate_weekly_report: запускается по расписанию каждый понедельник в 9:00.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery("task_flow", broker=settings.RABBITMQ_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
)


@celery_app.task(name="app.workers.celery_app.send_notification")
def send_notification(task_id: int, task_title: str, new_status: str) -> dict:
    """Отправляет уведомление о смене статуса задачи.

    В текущей реализации выводит сообщение в stdout.
    В продакшене здесь будет интеграция с email/Slack/Telegram.

    Args:
        task_id: идентификатор задачи.
        task_title: заголовок задачи для включения в уведомление.
        new_status: новый статус в виде строки.

    Returns:
        Словарь с результатом отправки.
    """
    print(f"[EMAIL] Задача #{task_id} '{task_title}' → {new_status}")
    return {"status": "sent", "task_id": task_id}


# Расписание периодических задач для Celery Beat
celery_app.conf.beat_schedule = {
    "weekly-report": {
        "task": "app.workers.celery_app.generate_weekly_report",
        # Каждый понедельник в 09:00 по московскому времени
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
    },
}


@celery_app.task(name="app.workers.celery_app.generate_weekly_report")
def generate_weekly_report() -> dict:
    """Генерирует еженедельный отчёт по активности пользователей.

    Запускается автоматически через Celery Beat по расписанию.
    В текущей реализации выводит сообщение в stdout.

    Returns:
        Словарь с результатом генерации.
    """
    print("[ОТЧЁТ] Генерация еженедельного отчёта...")
    return {"status": "generated"}
