"""Pydantic-схемы для операций с пользователями."""

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Данные для регистрации нового пользователя.

    Атрибуты:
        email: адрес электронной почты; валидируется через EmailStr.
        username: отображаемое имя пользователя.
        password: открытый пароль; хэшируется перед сохранением в БД.
    """

    email: EmailStr
    username: str
    password: str


class UserRead(BaseModel):
    """Публичные данные пользователя, возвращаемые в ответах API.

    Атрибуты:
        id: первичный ключ пользователя.
        email: адрес электронной почты.
        username: отображаемое имя.
    """

    id: int
    email: str
    username: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT-токен, возвращаемый после успешного входа.

    Атрибуты:
        access_token: подписанный JWT-токен для авторизации запросов.
        token_type: всегда "bearer" — стандартный тип для OAuth2.
    """

    access_token: str
    token_type: str = "bearer"
