"""ORM-модель пользователя.

ORM (Object-Relational Mapping) позволяет работать с таблицами БД
как с обычными Python-классами. SQLAlchemy транслирует методы
(db.add, db.get, select) в SQL-запросы автоматически.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Пользователь системы — таблица users в PostgreSQL.

    Mapped[тип] — синтаксис SQLAlchemy 2.0 для аннотации колонок.
    Python видит атрибут как обычное поле с типом,
    SQLAlchemy знает что это колонка таблицы.

    Атрибуты:
        id: первичный ключ. autoincrement по умолчанию.
        email: уникальный адрес электронной почты, используется для входа.
            unique=True → UNIQUE constraint в PostgreSQL
            index=True → индекс для быстрого поиска WHERE email = '...'
        username: уникальное отображаемое имя.
        hashed_password: bcrypt-хэш пароля, исходный пароль не хранится никогда.
        created_at: дата и время регистрации.
            server_default=func.now() → значение вставляет сам PostgreSQL,
            не Python. Так время всегда в таймзоне сервера БД.
        projects: виртуальное поле — список проектов пользователя.
            Не хранится в таблице users, загружается отдельным SELECT при обращении.
        tasks: виртуальное поле — задачи, назначенные на пользователя.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationship — "связь" между таблицами через внешние ключи.
    # back_populates="owner" означает: у Project есть поле owner,
    # которое ссылается обратно на User. SQLAlchemy синхронизирует их.
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    tasks: Mapped[list["Task"]] = relationship(back_populates="assignee")
