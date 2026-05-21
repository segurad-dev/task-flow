"""Утилиты безопасности: хэширование паролей и генерация JWT-токенов.

Почему пароли хэшируются, а не шифруются?
- Шифрование обратимо (можно расшифровать зная ключ)
- Хэширование необратимо: из хэша невозможно получить пароль
- При утечке БД злоумышленник видит только хэши — пароли в безопасности
- bcrypt специально спроектирован медленным (cost factor), что защищает
  от brute-force атак даже при утечке хэшей
"""

from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

# CryptContext управляет хэшированием паролей.
# schemes=["bcrypt"]: используем bcrypt — стандарт индустрии для паролей.
# deprecated="auto": если в БД есть хэши старых алгоритмов,
# passlib автоматически пометит их устаревшими при проверке.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хэширует открытый пароль с помощью bcrypt.

    bcrypt автоматически генерирует случайную соль (salt) для каждого
    вызова, поэтому hash_password("123") даёт разный результат
    при каждом вызове. Это защищает от rainbow-table атак.

    Не используй hashlib.sha256 или md5 для паролей — они слишком быстрые.

    Args:
        password: открытый пароль пользователя.

    Returns:
        Строка bcrypt-хэша вида "$2b$12$..." для хранения в БД.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Проверяет соответствие открытого пароля хэшу из БД.

    Нельзя просто сравнить hash_password(plain) == hashed,
    потому что bcrypt каждый раз генерирует разную соль.
    passlib.verify извлекает соль из хэша и корректно сравнивает.

    Args:
        plain: открытый пароль из формы входа.
        hashed: bcrypt-хэш из базы данных.

    Returns:
        True если пароль совпадает, False иначе.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """Генерирует подписанный JWT-токен с идентификатором пользователя.

    JWT (JSON Web Token) — это строка из трёх частей, разделённых точкой:
    1. Header: алгоритм подписи (HS256)
    2. Payload: данные (sub, exp) — НЕ зашифрованы, только подписаны!
    3. Signature: HMAC(header + payload, SECRET_KEY)

    Клиент получает токен при логине и прикладывает его к каждому запросу.
    Сервер проверяет подпись и извлекает user_id без обращения к БД.

    ВАЖНО: payload читаем без SECRET_KEY (base64 decode).
    Никогда не помещай в токен чувствительные данные (пароль, номер карты).

    Args:
        user_id: первичный ключ пользователя из таблицы users.

    Returns:
        Подписанный JWT-токен в виде строки "xxx.yyy.zzz".
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        # sub (subject) — стандартный JWT claim для идентификатора субъекта.
        # exp (expiration) — время истечения; jose проверяет его автоматически.
        # user_id передаём как str: JWT spec требует string в sub.
        {"sub": str(user_id), "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
