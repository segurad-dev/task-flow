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
    result = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(case((Task.status == TaskStatus.DONE, 1))).label("done"),
            func.count(case((Task.status == TaskStatus.IN_PROGRESS, 1))).label("in_progress"),
            func.count(case((Task.status == TaskStatus.TODO, 1))).label("todo"),
        ).where(Task.project_id == project_id)
    )
    row = result.one()
    avg_result = await db.execute(
        select(
            func.avg(
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
    result = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(case((Task.status == TaskStatus.DONE, 1))).label("done"),
        ).where(Task.assignee_id == current_user.id)
    )
    row = result.one()
    return {"user_id": current_user.id, "total_assigned": row.total, "completed": row.done}
