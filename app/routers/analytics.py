"""Роутер аналитики: статистика по проектам и личная статистика пользователя.

Здесь используются SQL-агрегации через SQLAlchemy ORM:
- func.count(): COUNT(*) — подсчёт строк
- func.case(): CASE WHEN ... THEN ... END — условный COUNT
- func.avg(): AVG() — среднее значение
- func.extract(): EXTRACT(epoch FROM ...) — перевод интервала в секунды

Два отдельных запроса вместо одного с JOIN: проще читать и отлаживать.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/project/{project_id}")
async def project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает статистику задач по проекту.

    Запрос 1 — счётчики по статусам:
    SQL эквивалент:
        SELECT
            COUNT(id) AS total,
            COUNT(CASE WHEN status = 'done' THEN 1 END) AS done,
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END) AS in_progress,
            COUNT(CASE WHEN status = 'todo' THEN 1 END) AS todo
        FROM tasks WHERE project_id = :project_id

    func.count(case((условие, 1))):
    - CASE WHEN условие THEN 1 END возвращает 1 если условие верно, иначе NULL
    - COUNT() считает только не-NULL значения → получаем условный COUNT

    Запрос 2 — среднее время выполнения:
    func.extract("epoch", интервал) → количество секунд в интервале.
    completed_at - created_at в PostgreSQL даёт тип INTERVAL.
    EXTRACT(epoch FROM INTERVAL) переводит в секунды (float).
    Делим на 3600 → часы.

    Args:
        project_id: идентификатор проекта из URL.
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Словарь с полями: total, done, in_progress, todo,
        completion_rate (%), avg_completion_hours.
    """
    result = await db.execute(
        select(
            # COUNT(id) — подсчёт всех задач проекта
            func.count(Task.id).label("total"),
            # COUNT(CASE WHEN status='done' THEN 1 END) — только выполненные
            func.count(case((Task.status == TaskStatus.DONE, 1))).label("done"),
            func.count(case((Task.status == TaskStatus.IN_PROGRESS, 1))).label("in_progress"),
            func.count(case((Task.status == TaskStatus.TODO, 1))).label("todo"),
        ).where(Task.project_id == project_id)
    )
    # result.one() ожидает ровно одну строку — агрегация всегда возвращает одну строку.
    # Если строк больше или меньше — бросает исключение.
    row = result.one()

    avg_result = await db.execute(
        select(
            func.avg(
                # EXTRACT(epoch FROM completed_at - created_at) → секунды выполнения
                # Работает только с PostgreSQL — функция epoch там встроена
                func.extract("epoch", Task.completed_at - Task.created_at)
            ).label("avg_seconds")
        ).where(
            Task.project_id == project_id,
            Task.status == TaskStatus.DONE,
            # is_not(None) → IS NOT NULL: учитываем только задачи с заполненным completed_at
            Task.completed_at.is_not(None),
        )
    )
    # scalar() возвращает одно значение (первый столбец первой строки).
    # or 0: если нет завершённых задач, AVG вернёт NULL → используем 0.
    avg_seconds = avg_result.scalar() or 0

    return {
        "project_id": project_id,
        "total": row.total,
        "done": row.done,
        "in_progress": row.in_progress,
        "todo": row.todo,
        # Защита от деления на ноль: если задач нет, rate = 0
        "completion_rate": round(row.done / row.total * 100, 1) if row.total else 0,
        # Переводим секунды в часы, округляем до 1 знака
        "avg_completion_hours": round(avg_seconds / 3600, 1),
    }


@router.get("/me")
async def my_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает личную статистику текущего пользователя.

    Более простой запрос чем project_stats: только два счётчика.
    Фильтрация по assignee_id — задачи назначенные на пользователя.

    Args:
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Словарь с полями: user_id, total_assigned, completed.
    """
    result = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(case((Task.status == TaskStatus.DONE, 1))).label("done"),
        ).where(Task.assignee_id == current_user.id)
    )
    row = result.one()
    return {"user_id": current_user.id, "total_assigned": row.total, "completed": row.done}
