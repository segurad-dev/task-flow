"""Роутер аутентификации: регистрация, вход и зависимость get_current_user.

Как работает аутентификация в целом:
1. Пользователь регистрируется: пароль хэшируется, user сохраняется в БД
2. Пользователь входит: сервер проверяет email+пароль, возвращает JWT-токен
3. Защищённые эндпоинты: клиент прикладывает токен в заголовке Authorization
4. Сервер проверяет подпись токена, извлекает user_id, загружает User из БД
5. Если всё ок — передаёт User в обработчик через Depends(get_current_user)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрирует нового пользователя.

    response_model=UserRead: FastAPI автоматически фильтрует ответ через схему.
    Даже если вернуть объект User со всеми полями, клиент получит только
    id, email, username — поле hashed_password не попадёт в ответ.

    status_code=201: Created — семантически правильный код для создания ресурса.

    Args:
        data: email, username и открытый пароль (валидируется Pydantic).
        db: сессия базы данных (внедряется через Depends(get_db)).

    Returns:
        Данные созданного пользователя (без пароля).

    Raises:
        HTTPException 400: если email уже зарегистрирован.
    """
    # db.scalar() выполняет SELECT и возвращает первый столбец первой строки.
    # Если пользователь найден — scalar вернёт объект User (truthy).
    # Если не найден — вернёт None (falsy).
    if await db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    user = User(
        email=data.email,
        username=data.username,
        # hash_password() — bcrypt хэш, исходный пароль нигде не сохраняется
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    # flush() отправляет INSERT в БД в рамках текущей транзакции.
    # Это заполняет user.id (autoincrement), но не фиксирует транзакцию.
    # commit() произойдёт в get_db() после завершения обработчика.
    await db.flush()
    return user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Аутентифицирует пользователя и возвращает JWT-токен.

    OAuth2PasswordRequestForm — стандартная FastAPI форма, которая ожидает
    Content-Type: application/x-www-form-urlencoded (не JSON!).
    Поле form.username используется как email (это стандарт OAuth2).

    Почему проверяем email и пароль вместе, а не по отдельности?
    Если бы возвращали разные ошибки ("email не найден" vs "неверный пароль"),
    злоумышленник мог бы перебирать email-адреса через разные статусы.
    Единое сообщение "Неверный email или пароль" это предотвращает.

    Args:
        form: форма с полями username (email) и password.
        db: сессия базы данных.

    Returns:
        JWT access_token для использования в заголовке Authorization.

    Raises:
        HTTPException 401: если email не найден или пароль неверен.
    """
    user = await db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return Token(access_token=create_access_token(user.id))


# OAuth2PasswordBearer — схема безопасности FastAPI.
# tokenUrl="/auth/login" — URL для получения токена (используется Swagger UI).
# При запросе к защищённому эндпоинту FastAPI автоматически извлекает токен
# из заголовка "Authorization: Bearer <token>" и передаёт в функцию.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Зависимость FastAPI: извлекает текущего пользователя из JWT-токена.

    Эта функция — ключевой элемент защиты API.
    Используется через Depends(get_current_user) в защищённых эндпоинтах:

        @router.get("/tasks/")
        async def get_tasks(current_user: User = Depends(get_current_user)):
            # current_user уже проверен и загружен из БД

    Цепочка зависимостей FastAPI:
    1. Запрос → FastAPI видит Depends(get_current_user)
    2. → Depends(oauth2_scheme) → извлекает token из заголовка Authorization
    3. → Depends(get_db) → открывает сессию БД
    4. → get_current_user(token, db) → проверяет токен, возвращает User

    Args:
        token: JWT-токен из заголовка Authorization: Bearer <token>.
        db: сессия базы данных.

    Returns:
        Объект User для аутентифицированного пользователя.

    Raises:
        HTTPException 401: если токен невалиден, истёк или пользователь удалён.
    """
    # Единая ошибка для всех случаев — не раскрываем причину отказа
    error = HTTPException(
        status_code=401,
        detail="Невалидный токен",
        # WWW-Authenticate: Bearer — стандартный заголовок для Bearer-схемы
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # jwt.decode проверяет подпись И время истечения (exp claim).
        # Если токен изменён или истёк — бросает JWTError.
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # sub хранит user_id как строку (JWT spec), конвертируем обратно в int
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        # JWTError: невалидная подпись или истёкший токен
        # KeyError: нет поля "sub" в payload
        # ValueError: sub не конвертируется в int
        raise error
    user = await db.get(User, user_id)
    if not user:
        # Пользователь мог быть удалён после выдачи токена
        raise error
    return user
