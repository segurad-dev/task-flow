"""Роутер аналитики: статистика по проектам и личная статистика пользователя."""

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

    Выполняет два SQL-запроса:
    1. Агрегация счётчиков по статусам через func.case (условный COUNT).
    2. Среднее время выполнения через func.extract("epoch", ...) для перевода
       интервала PostgreSQL в секунды.

    Args:
        project_id: идентификатор проекта.
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Словарь с полями: total, done, in_progress, todo,
        completion_rate (%), avg_completion_hours.
    """
    result = await db.execute(
        select(
            func.count(Task.id).label("total"),
            # func.case считает только строки, соответствующие условию
            func.count(case((Task.status == TaskStatus.DONE, 1))).label("done"),
            func.count(case((Task.status == TaskStatus.IN_PROGRESS, 1))).label("in_progress"),
            func.count(case((Task.status == TaskStatus.TODO, 1))).label("todo"),
        ).where(Task.project_id == project_id)
    )
    row = result.one()
    avg_result = await db.execute(
        select(
            func.avg(
                # extract("epoch", interval) переводит разность datetime в секунды
                func.extract("epoch", Task.completed_at - Task.created_at)
            ).label("avg_seconds")
        ).where(
            Task.project_id == project_id,
            Task.status == TaskStatus.DONE,
            Task.completed_at.is_not(None),
        )
    )
    avg_seconds = avg_result.scalar() or 0
    return {
        "project_id": project_id,
        "total": row.total,
        "done": row.done,
        "in_progress": row.in_progress,
        "todo": row.todo,
        "completion_rate": round(row.done / row.total * 100, 1) if row.total else 0,
        "avg_completion_hours": round(avg_seconds / 3600, 1),
    }


@router.get("/me")
async def my_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает личную статистику текущего пользователя.

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
