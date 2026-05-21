"""ORM-модель пользователя."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Пользователь системы.

    Атрибуты:
        id: первичный ключ.
        email: уникальный адрес электронной почты, используется для входа.
        username: уникальное отображаемое имя.
        hashed_password: bcrypt-хэш пароля, исходный пароль не хранится.
        created_at: дата и время регистрации, проставляется сервером БД.
        projects: проекты, которыми владеет пользователь.
        tasks: задачи, назначенные на пользователя.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    tasks: Mapped[list["Task"]] = relationship(back_populates="assignee")
