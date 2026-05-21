"""ORM-модель проекта."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    """Проект — контейнер для группировки задач.

    Атрибуты:
        id: первичный ключ.
        title: название проекта.
        description: необязательное описание.
        owner_id: внешний ключ на создателя проекта.
        created_at: дата создания, проставляется сервером БД.
        owner: объект пользователя-владельца.
        tasks: задачи проекта; удаляются вместе с проектом (cascade).
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    # cascade="all, delete-orphan": задачи удаляются при удалении проекта
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
