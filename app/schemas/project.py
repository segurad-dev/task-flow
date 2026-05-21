"""Pydantic-схемы для операций с проектами."""

from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    """Данные для создания нового проекта.

    Атрибуты:
        title: название проекта.
        description: необязательное описание.
    """

    title: str
    description: str | None = None


class ProjectRead(BaseModel):
    """Данные проекта, возвращаемые в ответах API.

    Атрибуты:
        id: первичный ключ проекта.
        title: название проекта.
        description: описание или None.
        owner_id: идентификатор пользователя-владельца.
        created_at: дата и время создания.
    """

    id: int
    title: str
    description: str | None
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
