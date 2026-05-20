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


@router.get("/", response_model=list[TaskRead])
async def get_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = f"tasks:{current_user.id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    result = await db.execute(select(Task).where(Task.assignee_id == current_user.id))
    tasks = result.scalars().all()
    data = [TaskRead.model_validate(t).model_dump(mode="json") for t in tasks]
    await redis_client.setex(cache_key, 60, json.dumps(data))
    return tasks


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    if task.status == TaskStatus.DONE and not task.completed_at:
        task.completed_at = datetime.utcnow()
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(task)
