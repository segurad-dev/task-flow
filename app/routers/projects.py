"""Роутер проектов: создание и получение списка проектов текущего пользователя."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectRead, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создаёт новый проект от имени текущего пользователя.

    Args:
        data: название и описание проекта.
        db: сессия базы данных.
        current_user: аутентифицированный пользователь — становится владельцем.

    Returns:
        Данные созданного проекта.
    """
    project = Project(**data.model_dump(), owner_id=current_user.id)
    db.add(project)
    await db.flush()
    return project


@router.get("/", response_model=list[ProjectRead])
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Возвращает список проектов текущего пользователя.

    Args:
        db: сессия базы данных.
        current_user: аутентифицированный пользователь.

    Returns:
        Список проектов, где пользователь является владельцем.
    """
    result = await db.execute(select(Project).where(Project.owner_id == current_user.id))
    return result.scalars().all()
