from celery import Celery

from app.config import settings

celery_app = Celery("task_flow", broker=settings.RABBITMQ_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
)
