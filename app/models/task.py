"""ORM-модель задачи и перечисление статусов."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    """Допустимые статусы задачи.

    Наследование от str позволяет сериализовать значение как строку
    без дополнительной конвертации в JSON и Pydantic-схемах.
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class Task(Base):
    """Задача внутри проекта.

    Атрибуты:
        id: первичный ключ.
        title: заголовок задачи.
        description: необязательное описание.
        status: текущий статус; по умолчанию TODO.
        project_id: внешний ключ проекта; задача удаляется вместе с проектом.
        assignee_id: внешний ключ исполнителя; при удалении пользователя — SET NULL.
        created_at: дата создания.
        updated_at: дата последнего изменения, обновляется автоматически.
        completed_at: момент завершения; используется в аналитике для расчёта avg времени.
        project: связанный объект проекта.
        assignee: связанный объект пользователя-исполнителя.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.TODO)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    # Проставляется вручную при переходе в статус DONE; не заполняется БД автоматически
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(back_populates="tasks")
