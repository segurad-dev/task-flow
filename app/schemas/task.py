"""Pydantic-схемы для операций с задачами."""

from datetime import datetime

from pydantic import BaseModel

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """Данные для создания новой задачи.

    Атрибуты:
        title: заголовок задачи.
        description: необязательное описание.
        project_id: идентификатор проекта, к которому относится задача.
        assignee_id: идентификатор исполнителя; можно не указывать.
    """

    title: str
    description: str | None = None
    project_id: int
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    """Данные для частичного обновления задачи (PATCH).

    Все поля необязательны: при десериализации используется
    model_dump(exclude_unset=True), чтобы обновлять только переданные поля.

    Атрибуты:
        title: новый заголовок.
        description: новое описание.
        status: новый статус из перечисления TaskStatus.
        assignee_id: новый исполнитель или None для снятия назначения.
    """

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    assignee_id: int | None = None


class TaskRead(BaseModel):
    """Полные данные задачи, возвращаемые в ответах API.

    Атрибуты:
        id: первичный ключ задачи.
        title: заголовок.
        description: описание или None.
        status: текущий статус.
        project_id: идентификатор проекта.
        assignee_id: идентификатор исполнителя или None.
        created_at: дата создания.
        updated_at: дата последнего изменения.
    """

    id: int
    title: str
    description: str | None
    status: TaskStatus
    project_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
