"""ORM-модель задачи и перечисление статусов."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    """Допустимые статусы задачи.

    Почему наследуем от str?
    Enum по умолчанию при сравнении/сериализации возвращает
    TaskStatus.DONE, а не строку "done".
    Наследование от str означает что TaskStatus.DONE == "done" → True,
    и json.dumps(TaskStatus.DONE) → "done" без дополнительной конвертации.

    Это особенно важно для Pydantic-схем и для сравнения со значениями из БД.
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class Task(Base):
    """Задача внутри проекта. Таблица tasks.

    Атрибуты:
        id: первичный ключ.
        title: заголовок задачи.
        description: необязательное описание.
        status: текущий статус.
            Enum(TaskStatus) → PostgreSQL ENUM тип, хранит только допустимые значения.
            default=TaskStatus.TODO → применяется на уровне Python при создании объекта.
        project_id: обязательный внешний ключ.
            ondelete="CASCADE": при удалении проекта задача тоже удаляется (на уровне БД).
        assignee_id: необязательный внешний ключ на исполнителя.
            ondelete="SET NULL": при удалении пользователя задача остаётся,
            но assignee_id становится NULL. Задача не теряется.
        created_at: дата создания, проставляется PostgreSQL.
        updated_at: дата последнего изменения.
            onupdate=func.now() → PostgreSQL обновляет это поле автоматически
            при каждом UPDATE. Python не должен делать это вручную.
        completed_at: момент завершения задачи.
            NULL до тех пор, пока статус не станет DONE.
            Проставляется вручную в роутере, а не автоматически сервером БД.
            Нужен для аналитики: вычисляем completed_at - created_at.
        project: объект Project (виртуальное поле, загружается при обращении).
        assignee: объект User или None (если исполнитель не назначен).
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
    # Не заполняется БД автоматически — роутер проставляет при переходе в DONE.
    # Это позволяет аналитике вычислить реальное время выполнения задачи.
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(back_populates="tasks")
