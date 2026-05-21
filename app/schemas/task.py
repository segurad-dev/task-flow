"""Pydantic-схемы для операций с задачами.

Зачем три отдельные схемы (Create/Update/Read)?

Create — входные данные при создании: только то, что нужно передать.
Update — частичное обновление: все поля Optional, передаём только то, что меняем.
Read — ответ API: все поля включая id и timestamps, которые генерирует БД.

Если использовать одну схему — придётся делать id обязательным при создании
(которого ещё нет) или необязательным в ответе (где он всегда есть).
Разделение решает это противоречие.
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """Данные для создания новой задачи.

    Атрибуты:
        title: заголовок задачи. Обязательное поле.
        description: необязательное описание. None по умолчанию.
        project_id: идентификатор проекта. Обязательное поле.
        assignee_id: идентификатор исполнителя. None = задача не назначена.
    """

    title: str
    description: str | None = None
    project_id: int
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    """Данные для частичного обновления задачи (PATCH).

    Все поля необязательны — клиент передаёт только то, что хочет изменить.

    Как это работает в роутере:
        data.model_dump(exclude_unset=True)
        → возвращает словарь только из переданных полей
        → {"status": "done"} вместо {"title": None, "description": None, ...}

    Без exclude_unset=True обновление {"status": "done"} затёрло бы
    description и другие поля значением None.

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

    model_config = {"from_attributes": True} позволяет Pydantic
    читать данные из SQLAlchemy-объектов (ORM instances).
    Без этого TaskRead.model_validate(task_orm_object) бросило бы ошибку,
    потому что Pydantic по умолчанию ожидает dict, а не ORM-объект.

    Атрибуты:
        id: первичный ключ задачи.
        title: заголовок.
        description: описание или None.
        status: текущий статус.
        project_id: идентификатор проекта.
        assignee_id: идентификатор исполнителя или None.
        created_at: дата создания (из БД).
        updated_at: дата последнего изменения (из БД).
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
