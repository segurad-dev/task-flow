from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.task import TaskCreate, TaskRead

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskRead, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**data.model_dump())
    db.add(task)
    await db.flush()
    return task
