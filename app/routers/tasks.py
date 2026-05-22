"""Роутер задач: CRUD с Redis-кэшированием и Celery-уведомлениями.

Этот файл — самый сложный в проекте, здесь пересекаются:
- FastAPI (HTTP-слой)
- SQLAlchemy (работа с БД)
- Redis (кэширование)
- Celery (фоновые задачи)
- Pydantic (сериализация)
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.workers.celery_app import send_notification

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskRead, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создаёт новую задачу и инвалидирует кэш списка задач пользователя.

    data.model_dump() конвертирует Pydantic-модель в dict:
    {"title": "...", "project_id": 1, "description": None, "assignee_id": None}
    Task(**dict) распаковывает dict в аргументы конструктора.

    После создания кэш списка задач устаревает — удаляем его,
    чтобы следующий GET /tasks/ загрузил свежие данные из БД.

    Args:
        data: данные задачи (заголовок, проект, исполнитель).
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Данные созданной задачи.
    """
    task = Task(**data.model_dump())
    db.add(task)
    # flush(): INSERT выполняется, task.id заполняется, но транзакция не закрыта.
    # Нужно до redis.delete, чтобы task существовал если что-то пойдёт не так.
    await db.flush()
    # Инвалидируем оба варианта ключа: по проекту и общий список
    await redis_client.delete(f"tasks:{current_user.id}:{task.project_id}")
    await redis_client.delete(f"tasks:{current_user.id}:all")
    return task


@router.get("/", response_model=list[TaskRead])
async def get_tasks(
    status: TaskStatus | None = None,
    project_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает список задач текущего пользователя с кэшированием.

    Стратегия кэша (cache-aside):
    1. Проверяем Redis по ключу tasks:{user_id}
    2. Cache hit → десериализуем JSON и возвращаем без обращения к БД
    3. Cache miss → запрос к PostgreSQL, сериализуем в JSON, кладём в Redis на 60с

    ОГРАНИЧЕНИЕ: кэш не учитывает параметры фильтрации и пагинации.
    Если кэш есть — возвращаем его, игнорируя status/skip/limit.
    Это упрощение для портфолио; в продакшене ключ должен включать параметры.

    Args:
        status: опциональный фильтр по статусу задачи.
        skip: смещение для пагинации (OFFSET в SQL).
        limit: максимальное количество задач (LIMIT в SQL).
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Список задач, назначенных на текущего пользователя.
    """
    # Ключ кэша включает project_id, чтобы не смешивать разные выборки
    cache_key = f"tasks:{current_user.id}:{project_id or 'all'}"
    cached = await redis_client.get(cache_key)
    if cached:
        # json.loads: str → list[dict]. FastAPI применит response_model поверх.
        return json.loads(cached)

    # Строим SQL-запрос через ORM (не raw SQL).
    # select(Task) → SELECT * FROM tasks
    if project_id:
        # Когда передан project_id — возвращаем все задачи проекта
        query = select(Task).where(Task.project_id == project_id)
    else:
        query = select(Task).where(Task.assignee_id == current_user.id)
    if status:
        # Добавляем WHERE status = '...' только если передан параметр
        query = query.where(Task.status == status)
    # OFFSET skip LIMIT limit — стандартная пагинация
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    # scalars() извлекает первый столбец (ORM-объекты Task).
    # all() собирает в список. Без all() — ленивый итератор.
    tasks = result.scalars().all()

    # Сериализуем для Redis: ORM-объекты нельзя хранить напрямую.
    # model_validate(orm_obj) → Pydantic-объект → model_dump(mode="json") → dict
    # mode="json" конвертирует datetime в ISO-строки (json.dumps принимает только primitives).
    data = [TaskRead.model_validate(t).model_dump(mode="json") for t in tasks]
    # setex: SET + EXPIRE. Сохраняем на 60 секунд.
    await redis_client.setex(cache_key, 60, json.dumps(data))

    return tasks


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает задачу по идентификатору.

    db.get(Model, pk) — аналог SELECT ... WHERE id = pk.
    Использует кэш идентичности сессии: если объект уже загружен в этой
    сессии, повторный db.get() вернёт его без SQL-запроса.

    Args:
        task_id: первичный ключ задачи из URL.
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Данные задачи.

    Raises:
        HTTPException 404: если задача не найдена.
    """
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Частично обновляет задачу (PATCH — только переданные поля).

    Ключевые моменты:
    1. model_dump(exclude_unset=True) → только поля из запроса, не все Optional=None
    2. setattr(task, field, value) → ORM замечает изменение, генерирует UPDATE
    3. completed_at проставляется один раз при первом переходе в DONE
    4. Уведомление через Celery — только при смене статуса, не при каждом PATCH
    5. Инвалидация кэша — при любом изменении задачи

    Args:
        task_id: первичный ключ задачи из URL.
        data: поля для обновления (только переданные в запросе).
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Обновлённые данные задачи.

    Raises:
        HTTPException 404: если задача не найдена.
    """
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Сохраняем старый статус до применения изменений — нужен для сравнения ниже
    old_status = task.status

    # exclude_unset=True — ключевой момент PATCH-семантики.
    # PATCH {"status": "done"} → {"status": "done"} (не {"title": None, ...})
    for field, value in data.model_dump(exclude_unset=True).items():
        # setattr применяет изменение к ORM-объекту.
        # SQLAlchemy отслеживает измененные поля через __set_name__ дескрипторы.
        setattr(task, field, value)

    # Автоматически проставляем время завершения при первом переходе в DONE.
    # Проверяем completed_at чтобы не перезатереть при повторном PATCH status=done.
    if task.status == TaskStatus.DONE and not task.completed_at:
        task.completed_at = datetime.utcnow()

    # Отправляем уведомление только при реальной смене статуса.
    # .delay() — асинхронный вызов Celery: задача уходит в RabbitMQ мгновенно,
    # HTTP-запрос не ждёт отправки уведомления.
    if data.status and data.status != old_status:
        send_notification.delay(task_id=task.id, task_title=task.title, new_status=data.status.value)

    # Инвалидируем оба варианта ключа: по проекту и общий список
    await redis_client.delete(f"tasks:{current_user.id}:{task.project_id}")
    await redis_client.delete(f"tasks:{current_user.id}:all")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удаляет задачу и инвалидирует кэш списка задач пользователя.

    status_code=204: No Content — стандартный код для успешного удаления.
    FastAPI при 204 не включает тело в ответ (даже если return что-то вернуть).

    Args:
        task_id: первичный ключ задачи из URL.
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Raises:
        HTTPException 404: если задача не найдена.
    """
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    # db.delete() помечает объект для удаления.
    # Реальный DELETE выполнится при commit() в get_db().
    await db.delete(task)
    await redis_client.delete(f"tasks:{current_user.id}:{task.project_id}")
    await redis_client.delete(f"tasks:{current_user.id}:all")
