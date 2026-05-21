"""Утилиты безопасности: хэширование паролей и генерация JWT-токенов."""

from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хэширует открытый пароль с помощью bcrypt.

    Args:
        password: открытый пароль пользователя.

    Returns:
        Строка bcrypt-хэша для хранения в БД.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Проверяет соответствие открытого пароля хэшу из БД.

    Args:
        plain: открытый пароль из формы входа.
        hashed: bcrypt-хэш из базы данных.

    Returns:
        True если пароль совпадает, False иначе.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """Генерирует подписанный JWT-токен с идентификатором пользователя.

    Токен содержит два claim-а: sub (user_id) и exp (время истечения).
    Подписывается SECRET_KEY алгоритмом из настроек (по умолчанию HS256).

    Args:
        user_id: первичный ключ пользователя из таблицы users.

    Returns:
        Подписанный JWT-токен в виде строки.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
