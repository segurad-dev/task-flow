"""ORM-модель проекта."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    """Проект — контейнер для группировки задач. Таблица projects.

    Атрибуты:
        id: первичный ключ.
        title: название проекта. String(200) → VARCHAR(200) в PostgreSQL.
        description: необязательное описание.
            Mapped[str | None] означает что поле может быть None (NULL в БД).
            nullable=True дублирует это на уровне колонки.
        owner_id: внешний ключ — ссылается на users.id.
            ondelete="CASCADE": при удалении пользователя проект тоже удаляется.
            Это правило на уровне БД, работает даже в обход Python-кода.
        created_at: дата создания, проставляется сервером БД.
        owner: объект пользователя-владельца (загружается через JOIN при обращении).
        tasks: задачи проекта. cascade="all, delete-orphan" означает:
            при удалении Project SQLAlchemy сначала удалит все связанные Task,
            затем сам Project. Это правило на уровне Python/SQLAlchemy,
            дополняет ondelete="CASCADE" на уровне БД.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    # cascade="all, delete-orphan": удаляй задачи вместе с проектом.
    # Без этого SQLAlchemy попытался бы оставить задачи с project_id=NULL
    # что нарушило бы NOT NULL constraint колонки.
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
