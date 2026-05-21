"""Celery-приложение: конфигурация, задачи и расписание.

Celery — это система выполнения задач в фоне.
Зачем нужны фоновые задачи?
- HTTP-запрос должен отвечать быстро (< 200ms)
- Отправка email, генерация отчётов, тяжёлые вычисления — медленные операции
- Решение: HTTP-запрос ставит задачу в очередь и сразу отвечает клиенту,
  Celery Worker выполняет задачу асинхронно в отдельном процессе

Компоненты:
- Broker (RabbitMQ): принимает и хранит очередь задач
- Worker: процесс, который берёт задачи из очереди и выполняет
- Beat: планировщик, добавляет задачи в очередь по расписанию
- Backend (Redis): хранит результаты выполненных задач

Почему RabbitMQ как broker, а не Redis?
RabbitMQ специально создан для очередей сообщений:
- подтверждение доставки (если Worker упал, задача не потеряется)
- приоритеты очередей
- надёжная маршрутизация
Redis удобен, но может потерять задачи при перезапуске без AOF/RDB.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Создаём Celery-приложение.
# broker: откуда брать задачи (RabbitMQ)
# backend: куда сохранять результаты (Redis)
celery_app = Celery("task_flow", broker=settings.RABBITMQ_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    # Сериализация задач в JSON — читаемый формат, безопаснее pickle.
    # Pickle позволяет выполнить произвольный Python при десериализации.
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Таймзона для Celery Beat расписания.
    # Влияет только на crontab, не на сами задачи.
    timezone="Europe/Moscow",
)


@celery_app.task(name="app.workers.celery_app.send_notification")
def send_notification(task_id: int, task_title: str, new_status: str) -> dict:
    """Отправляет уведомление о смене статуса задачи.

    Декоратор @celery_app.task превращает обычную функцию в Celery-задачу.
    name= нужен для гарантированной адресации задачи по имени
    (без него имя генерируется автоматически и может меняться при рефакторинге).

    Вызов из роутера: send_notification.delay(task_id=..., ...)
    .delay() — асинхронный вызов: сериализует аргументы, отправляет в RabbitMQ,
    возвращает управление сразу. Worker выполнит задачу независимо.

    В текущей реализации выводит сообщение в stdout.
    В продакшене здесь будет интеграция с email/Slack/Telegram.

    Args:
        task_id: идентификатор задачи.
        task_title: заголовок задачи для включения в уведомление.
        new_status: новый статус в виде строки.

    Returns:
        Словарь с результатом — сохраняется в Redis backend.
    """
    print(f"[EMAIL] Задача #{task_id} '{task_title}' → {new_status}")
    return {"status": "sent", "task_id": task_id}


# beat_schedule — расписание для Celery Beat.
# Beat — это отдельный процесс (celery beat), который читает расписание
# и добавляет задачи в очередь в нужное время.
# Сам Beat не выполняет задачи — только ставит в очередь для Worker.
celery_app.conf.beat_schedule = {
    "weekly-report": {
        "task": "app.workers.celery_app.generate_weekly_report",
        # crontab(hour=9, minute=0, day_of_week="monday"):
        # запускать каждый понедельник в 09:00 (по timezone="Europe/Moscow")
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
    },
}


@celery_app.task(name="app.workers.celery_app.generate_weekly_report")
def generate_weekly_report() -> dict:
    """Генерирует еженедельный отчёт по активности пользователей.

    Запускается автоматически через Celery Beat по расписанию
    (каждый понедельник в 09:00). Не требует явного вызова из кода.

    В текущей реализации выводит сообщение в stdout.
    В продакшене здесь будет генерация PDF и отправка на email администраторам.

    Returns:
        Словарь с результатом — сохраняется в Redis backend.
    """
    print("[ОТЧЁТ] Генерация еженедельного отчёта...")
    return {"status": "generated"}
