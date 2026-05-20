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
def send_notification(task_id: int, task_title: str, new_status: str):
    print(f"[EMAIL] Задача #{task_id} '{task_title}' → {new_status}")
    return {"status": "sent", "task_id": task_id}


celery_app.conf.beat_schedule = {
    "weekly-report": {
        "task": "app.workers.celery_app.generate_weekly_report",
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
    },
}


@celery_app.task(name="app.workers.celery_app.generate_weekly_report")
def generate_weekly_report():
    print("[ОТЧЁТ] Генерация еженедельного отчёта...")
    return {"status": "generated"}
