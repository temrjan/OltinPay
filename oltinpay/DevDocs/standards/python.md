# PYTHON CODE STYLE GUIDE v2.0
## Для Claude Code — Максимальное качество кода

> **Цель:** Автоматическое следование лучшим практикам Python
> **Основа:** Google Python Style Guide + PEP8 + Modern Python 3.11+
> **Оптимизировано:** Для контекстного окна Claude Code

---

## 🎯 КЛЮЧЕВЫЕ ПРИНЦИПЫ

```
ВСЕГДА                              НИКОГДА
────────────────────────────────    ────────────────────────────────
✓ Type hints для всего              ✗ import *
✓ Google docstrings                 ✗ Широкий except без re-raise
✓ 4 пробела (NO TABS)               ✗ Mutable defaults: def f(x=[])
✓ 88 символов макс. (Black)         ✗ eval() / exec()
✓ snake_case функции/переменные     ✗ Хардкод секретов
✓ PascalCase классы                 ✗ print() в продакшене
✓ SCREAMING_SNAKE_CASE константы    ✗ SQL f-strings
✓ f-strings форматирование          ✗ Блокирующий код в async
✓ Параметризованные SQL             ✗ Игнорирование ошибок молча
✓ Context managers (with)           ✗ camelCase (это не Java)
```

---

## 📦 ИМПОРТЫ

```python
# ═══════════════════════════════════════════════════════════════════
# ПОРЯДОК: stdlib → third-party → local (пустая строка между группами)
# ═══════════════════════════════════════════════════════════════════

# 1. Стандартная библиотека
import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path
from typing import Any, Self, TypeAlias

# 2. Сторонние библиотеки
import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Локальные модули
from app.core.config import settings
from app.models import User
from app.services import UserService

# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО
# ═══════════════════════════════════════════════════════════════════
from app.models import *              # Никогда!
import os, sys, json                  # Один импорт на строку
from typing import Optional,List      # Пробелы после запятых!
```

---

## 🏷 TYPE HINTS (Обязательны!)

```python
# ═══════════════════════════════════════════════════════════════════
# Python 3.10+ синтаксис (предпочтительный)
# ═══════════════════════════════════════════════════════════════════

# Базовые типы
def get_user(user_id: str) -> User | None:
    """Union через | вместо Optional."""
    ...

def process_items(items: list[str]) -> dict[str, int]:
    """Встроенные generics вместо typing.List/Dict."""
    ...

# Type aliases для сложных типов
UserId: TypeAlias = str
UserDict: TypeAlias = dict[str, Any]
Callback: TypeAlias = Callable[[str], None]

# Generics в классах
class Repository[T]:
    """Generic repository для любых моделей."""

    def __init__(self, model: type[T]) -> None:
        self._model = model

    async def get(self, id: str) -> T | None:
        ...

# Self для методов возвращающих себя
class Builder:
    def with_name(self, name: str) -> Self:
        self._name = name
        return self

# ═══════════════════════════════════════════════════════════════════
# Python 3.9 fallback (если нужна совместимость)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional, List, Dict, Union

def get_user(user_id: str) -> Optional[User]:
    ...

def process_items(items: List[str]) -> Dict[str, int]:
    ...

# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО
# ═══════════════════════════════════════════════════════════════════
def get_user(user_id):              # Нет type hints!
    ...

def process(items: list):           # Неполный generic
    ...

def fetch(data: dict) -> dict:      # Нет параметров generic
    ...
```

---

## 📝 DOCSTRINGS (Google Style)

```python
# ═══════════════════════════════════════════════════════════════════
# ПОЛНЫЙ ФОРМАТ — для сложных функций
# ═══════════════════════════════════════════════════════════════════

async def fetch_user_data(
    user_id: str,
    *,
    include_deleted: bool = False,
    timeout: float = 30.0,
) -> UserDict:
    """Fetch user data from the database.

    Retrieves user information including profile, preferences,
    and activity history. Supports fetching soft-deleted users.

    Args:
        user_id: Unique identifier (UUID format).
        include_deleted: Include soft-deleted users. Defaults to False.
        timeout: Max wait time in seconds. Defaults to 30.0.

    Returns:
        Dictionary with user data:
            - id: User's unique identifier
            - name: Full name
            - email: Email address
            - is_active: Account status

    Raises:
        ValueError: If user_id is not valid UUID.
        UserNotFoundError: If user doesn't exist.
        DatabaseError: On connection failure.

    Example:
        >>> user = await fetch_user_data("550e8400-e29b-41d4-a716-446655440000")
        >>> print(user["name"])
        'John Doe'
    """
    ...


class UserRepository:
    """Repository for user data operations.

    Provides CRUD operations and complex queries for users table.
    Handles connection pooling automatically.

    Attributes:
        db: Database session instance.
        cache: In-memory cache for frequent queries.

    Example:
        >>> repo = UserRepository(session)
        >>> user = await repo.get_by_id("123")
        >>> await repo.update(user.id, {"name": "New Name"})
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            db: Active async database session.
        """
        self.db = db
        self.cache: dict[str, User] = {}

# ═══════════════════════════════════════════════════════════════════
# КРАТКИЙ ФОРМАТ — для простых функций
# ═══════════════════════════════════════════════════════════════════

def validate_email(email: str) -> bool:
    """Check if email format is valid."""
    return "@" in email and "." in email.split("@")[-1]

def calculate_total(prices: list[float]) -> float:
    """Sum all prices and return total."""
    return sum(prices)

async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
```

---

## 🏗 СТРУКТУРЫ ДАННЫХ

### Dataclasses — для простых данных

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True, slots=True)
class UserId:
    """Value object for user identifier."""
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) < 3:
            raise ValueError(f"Invalid user ID: {self.value}")


@dataclass(slots=True)
class User:
    """User domain model."""
    id: str
    name: str
    email: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    tags: list[str] = field(default_factory=list)  # ✓ Mutable через factory!

    def __post_init__(self) -> None:
        """Validate after initialization."""
        if "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")


# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО — mutable defaults
# ═══════════════════════════════════════════════════════════════════
@dataclass
class BadUser:
    tags: list[str] = []  # BUG! Общий список для всех экземпляров!
```

### Pydantic — для валидации и API

```python
from pydantic import BaseModel, Field, EmailStr, field_validator

class UserCreate(BaseModel):
    """Request model for user creation."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
            }
        }
    }


class UserResponse(BaseModel):
    """Response model for user data."""

    id: str
    name: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}  # Для ORM моделей
```

### Enum — для констант и статусов

```python
from enum import Enum, StrEnum, auto

class UserRole(StrEnum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class ProcessingStatus(Enum):
    """Processing status enumeration."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


# Использование
def check_access(user: User) -> bool:
    match user.role:
        case UserRole.ADMIN:
            return True
        case UserRole.USER:
            return user.is_active
        case UserRole.GUEST:
            return False
        case _:
            raise ValueError(f"Unknown role: {user.role}")
```

---

## 🔀 MATCH-CASE (Python 3.10+)

```python
# ═══════════════════════════════════════════════════════════════════
# Структурный паттерн-матчинг — мощная замена if/elif
# ═══════════════════════════════════════════════════════════════════

def handle_response(response: dict[str, Any]) -> str:
    """Process API response based on structure."""
    match response:
        case {"status": "ok", "data": data}:
            return f"Success: {data}"

        case {"status": "error", "code": code, "message": msg}:
            return f"Error {code}: {msg}"

        case {"status": "error", "message": msg}:
            return f"Error: {msg}"

        case _:
            return "Unknown response format"


def process_command(command: str, *args: str) -> None:
    """Process CLI command with arguments."""
    match command, args:
        case "help", ():
            show_help()

        case "get", (user_id,):
            get_user(user_id)

        case "create", (name, email):
            create_user(name, email)

        case "delete", (user_id, "--force"):
            delete_user(user_id, force=True)

        case _:
            print(f"Unknown command: {command}")


def classify_http_status(status: int) -> str:
    """Classify HTTP status code."""
    match status:
        case 200 | 201 | 204:
            return "success"
        case code if 400 <= code < 500:
            return "client_error"
        case code if 500 <= code < 600:
            return "server_error"
        case _:
            return "unknown"
```

---

## 🔥 ОБРАБОТКА ОШИБОК

```python
# ═══════════════════════════════════════════════════════════════════
# Кастомные исключения
# ═══════════════════════════════════════════════════════════════════

class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(AppError):
    """Raised when input validation fails."""
    pass


class NotFoundError(AppError):
    """Raised when requested resource doesn't exist."""
    pass


class DatabaseError(AppError):
    """Raised on database operation failure."""
    pass


# ═══════════════════════════════════════════════════════════════════
# Правильная обработка
# ═══════════════════════════════════════════════════════════════════

async def get_user(user_id: str) -> User:
    """Fetch user by ID with proper error handling.

    Args:
        user_id: User's unique identifier.

    Returns:
        User object.

    Raises:
        ValidationError: If user_id format is invalid.
        NotFoundError: If user doesn't exist.
        DatabaseError: On database failure.
    """
    # 1. Валидация входных данных
    if not user_id or not is_valid_uuid(user_id):
        raise ValidationError(f"Invalid user ID format: {user_id}", code="INVALID_ID")

    # 2. Попытка получить данные
    try:
        result = await db.fetch_one(
            "SELECT * FROM users WHERE id = :id",
            {"id": user_id}
        )
    except Exception as e:
        logger.error("Database query failed", extra={"user_id": user_id}, exc_info=True)
        raise DatabaseError("Failed to fetch user") from e

    # 3. Проверка результата
    if result is None:
        raise NotFoundError(f"User {user_id} not found", code="USER_NOT_FOUND")

    return User(**result)


# ═══════════════════════════════════════════════════════════════════
# Context managers для ресурсов
# ═══════════════════════════════════════════════════════════════════

async def process_file(filepath: Path) -> dict[str, Any]:
    """Process JSON file safely."""
    try:
        async with aiofiles.open(filepath) as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        raise NotFoundError(f"File not found: {filepath}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {filepath}: {e}")


# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО
# ═══════════════════════════════════════════════════════════════════

async def bad_get_user(user_id: str) -> User | None:
    try:
        return await db.fetch_one("SELECT * FROM users WHERE id = ?", user_id)
    except:                    # ❌ Слишком широко!
        pass                   # ❌ Молчаливое игнорирование!
    return None


def bad_process_file(filepath: str) -> dict:
    f = open(filepath)         # ❌ Нет автоматического закрытия!
    return json.loads(f.read())
```

---

## ⚡ ASYNC/AWAIT

```python
import asyncio
from collections.abc import AsyncIterator

# ═══════════════════════════════════════════════════════════════════
# Правильный async код
# ═══════════════════════════════════════════════════════════════════

async def fetch_user(client: httpx.AsyncClient, user_id: str) -> User:
    """Fetch single user."""
    response = await client.get(f"/users/{user_id}")
    response.raise_for_status()
    return User(**response.json())


async def fetch_users(user_ids: list[str]) -> list[User]:
    """Fetch multiple users concurrently."""
    async with httpx.AsyncClient(base_url=settings.API_URL) as client:
        tasks = [fetch_user(client, uid) for uid in user_ids]
        return await asyncio.gather(*tasks, return_exceptions=True)


async def fetch_with_semaphore(
    user_ids: list[str],
    max_concurrent: int = 10,
) -> list[User]:
    """Fetch users with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(uid: str) -> User:
        async with semaphore:
            return await fetch_user(uid)

    tasks = [fetch_one(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)


async def stream_users(batch_size: int = 100) -> AsyncIterator[User]:
    """Stream users from database in batches."""
    offset = 0
    while True:
        users = await db.fetch_all(
            "SELECT * FROM users ORDER BY id LIMIT :limit OFFSET :offset",
            {"limit": batch_size, "offset": offset}
        )

        if not users:
            break

        for user in users:
            yield User(**user)

        offset += batch_size


# Использование async generator
async def process_all_users() -> None:
    async for user in stream_users(batch_size=50):
        await process_user(user)


# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО
# ═══════════════════════════════════════════════════════════════════

async def bad_fetch_user(user_id: str) -> User:
    import requests
    response = requests.get(f"/users/{user_id}")  # ❌ Блокирующий вызов!
    return User(**response.json())


async def bad_fetch_all(ids: list[str]) -> list[User]:
    result = []
    for uid in ids:
        user = await fetch_user(uid)  # ❌ Последовательно вместо параллельно!
        result.append(user)
    return result
```

---

## 🧪 ТЕСТИРОВАНИЕ (pytest)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_user() -> User:
    """Create sample user for tests."""
    return User(
        id="test-123",
        name="John Doe",
        email="john@example.com",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
async def db_session():
    """Create test database session."""
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create mock HTTP client."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


# ═══════════════════════════════════════════════════════════════════
# Test classes — AAA pattern (Arrange, Act, Assert)
# ═══════════════════════════════════════════════════════════════════

class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_user_when_exists(
        self,
        db_session: AsyncSession,
        sample_user: User,
    ) -> None:
        """Should return user when ID exists in database."""
        # Arrange
        repo = UserRepository(db_session)
        await repo.create(sample_user)

        # Act
        result = await repo.get_by_id(sample_user.id)

        # Assert
        assert result is not None
        assert result.id == sample_user.id
        assert result.email == sample_user.email

    @pytest.mark.asyncio
    async def test_get_by_id_raises_not_found_when_missing(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Should raise NotFoundError when user doesn't exist."""
        # Arrange
        repo = UserRepository(db_session)

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await repo.get_by_id("nonexistent-id")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_stores_user_correctly(
        self,
        db_session: AsyncSession,
        sample_user: User,
    ) -> None:
        """Should store user and return with ID."""
        # Arrange
        repo = UserRepository(db_session)

        # Act
        created = await repo.create(sample_user)
        retrieved = await repo.get_by_id(created.id)

        # Assert
        assert retrieved is not None
        assert retrieved.name == sample_user.name


# ═══════════════════════════════════════════════════════════════════
# Parametrized tests
# ═══════════════════════════════════════════════════════════════════

class TestEmailValidation:
    """Tests for email validation."""

    @pytest.mark.parametrize(
        ("email", "expected"),
        [
            ("valid@example.com", True),
            ("user.name@domain.co.uk", True),
            ("user+tag@example.com", True),
            ("invalid-email", False),
            ("@example.com", False),
            ("user@", False),
            ("", False),
        ],
        ids=[
            "valid_simple",
            "valid_subdomain",
            "valid_with_tag",
            "missing_at",
            "missing_local",
            "missing_domain",
            "empty_string",
        ],
    )
    def test_email_validation(self, email: str, expected: bool) -> None:
        """Test email validation with various inputs."""
        result = validate_email(email)
        assert result == expected


# ═══════════════════════════════════════════════════════════════════
# Mocking external services
# ═══════════════════════════════════════════════════════════════════

class TestUserService:
    """Tests for UserService with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_fetch_user_calls_api_correctly(
        self,
        mock_http_client: MagicMock,
    ) -> None:
        """Should call external API with correct parameters."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "John"}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        service = UserService(client=mock_http_client)

        # Act
        user = await service.fetch_user("123")

        # Assert
        mock_http_client.get.assert_called_once_with("/users/123")
        assert user.id == "123"
        assert user.name == "John"

    @pytest.mark.asyncio
    async def test_fetch_user_raises_on_api_error(
        self,
        mock_http_client: MagicMock,
    ) -> None:
        """Should raise appropriate error when API fails."""
        # Arrange
        mock_http_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        service = UserService(client=mock_http_client)

        # Act & Assert
        with pytest.raises(NotFoundError):
            await service.fetch_user("nonexistent")


# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО
# ═══════════════════════════════════════════════════════════════════

def test1():                           # ❌ Плохое имя
    user = get_user("123")
    assert user                        # ❌ Неясная проверка

def test_user():                       # ❌ Что тестируем?
    assert True                        # ❌ Бессмысленный тест
```

---

## 🔒 БЕЗОПАСНОСТЬ

```python
import os
import secrets
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Секреты — ТОЛЬКО из переменных окружения
# ═══════════════════════════════════════════════════════════════════

class Settings(BaseModel):
    """Application settings from environment."""

    database_url: str = Field(alias="DATABASE_URL")
    api_key: str = Field(alias="API_KEY")
    secret_key: str = Field(alias="SECRET_KEY")
    debug: bool = Field(default=False, alias="DEBUG")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # Загрузит из .env автоматически


# ═══════════════════════════════════════════════════════════════════
# SQL — ТОЛЬКО параметризованные запросы
# ═══════════════════════════════════════════════════════════════════

# ✅ ПРАВИЛЬНО
async def get_user_by_email(email: str) -> User | None:
    """Fetch user by email safely."""
    result = await db.fetch_one(
        "SELECT * FROM users WHERE email = :email",
        {"email": email}
    )
    return User(**result) if result else None


async def create_user(name: str, email: str) -> User:
    """Create user with parameterized query."""
    result = await db.execute(
        "INSERT INTO users (name, email) VALUES (:name, :email) RETURNING *",
        {"name": name, "email": email}
    )
    return User(**result)


# ❌ КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО — SQL Injection!
async def bad_get_user(email: str) -> User:
    result = await db.fetch_one(
        f"SELECT * FROM users WHERE email = '{email}'"  # ❌ УЯЗВИМОСТЬ!
    )
    return User(**result)


# ═══════════════════════════════════════════════════════════════════
# Логирование — маскировка чувствительных данных
# ═══════════════════════════════════════════════════════════════════

def mask_email(email: str) -> str:
    """Mask email for logging."""
    if "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    return f"{local[:2]}***@{domain}"


def mask_token(token: str) -> str:
    """Mask token for logging."""
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


async def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate user safely."""
    logger.info(
        "Authentication attempt",
        extra={
            "email": mask_email(email),
            # ❌ НИКОГДА не логируем пароль!
        }
    )

    user = await get_user_by_email(email)
    if user and verify_password(password, user.password_hash):
        logger.info("Authentication successful", extra={"user_id": user.id})
        return user

    logger.warning("Authentication failed", extra={"email": mask_email(email)})
    return None


# ═══════════════════════════════════════════════════════════════════
# Генерация токенов и хэширование
# ═══════════════════════════════════════════════════════════════════

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token."""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """Hash password with salt."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        iterations=100_000,
    )
    return f"{salt}${hash_obj.hex()}"


# ═══════════════════════════════════════════════════════════════════
# ❌ КАТЕГОРИЧЕСКИ НЕПРАВИЛЬНО
# ═══════════════════════════════════════════════════════════════════

DATABASE_URL = "postgresql://user:password@localhost/db"  # ❌ НИКОГДА!
API_KEY = "sk_live_abc123xyz"                              # ❌ НИКОГДА!

logger.info(f"User {email} logged in with password {password}")  # ❌ НИКОГДА!
```

---

## 📊 ПРОИЗВОДИТЕЛЬНОСТЬ

```python
from functools import lru_cache, cache
import asyncio

# ═══════════════════════════════════════════════════════════════════
# Кэширование
# ═══════════════════════════════════════════════════════════════════

@lru_cache(maxsize=128)
def expensive_computation(n: int) -> int:
    """Cached computation for expensive operations."""
    # Для синхронных функций
    return sum(range(n))


@cache  # Python 3.9+ — unbounded cache
def get_config(key: str) -> str:
    """Cache configuration values."""
    return load_config()[key]


# Для async — используем словарь или aiocache
_user_cache: dict[str, User] = {}

async def get_user_cached(user_id: str) -> User:
    """Get user with simple caching."""
    if user_id not in _user_cache:
        _user_cache[user_id] = await fetch_user_from_db(user_id)
    return _user_cache[user_id]


# ═══════════════════════════════════════════════════════════════════
# List comprehensions vs loops
# ═══════════════════════════════════════════════════════════════════

# ✅ ХОРОШО — comprehensions
active_emails = [u.email for u in users if u.is_active]
user_by_id = {u.id: u for u in users}
unique_domains = {email.split("@")[1] for email in emails}

# ❌ НЕ ТАК ХОРОШО — явные циклы для простых случаев
active_emails = []
for user in users:
    if user.is_active:
        active_emails.append(user.email)


# ═══════════════════════════════════════════════════════════════════
# Генераторы для больших данных
# ═══════════════════════════════════════════════════════════════════

def read_large_file(filepath: Path) -> Iterator[str]:
    """Read file line by line — memory efficient."""
    with open(filepath) as f:
        for line in f:
            yield line.strip()


def process_in_chunks(items: list[T], chunk_size: int = 100) -> Iterator[list[T]]:
    """Process items in chunks."""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


# ═══════════════════════════════════════════════════════════════════
# Избегаем N+1 запросов
# ═══════════════════════════════════════════════════════════════════

# ❌ N+1 проблема
async def bad_get_users_with_posts() -> list[User]:
    users = await db.fetch_all("SELECT * FROM users")
    for user in users:
        user.posts = await db.fetch_all(
            "SELECT * FROM posts WHERE user_id = :id",
            {"id": user.id}
        )  # N дополнительных запросов!
    return users


# ✅ JOIN или подзапрос
async def get_users_with_posts() -> list[User]:
    """Fetch users with posts in single query."""
    return await db.fetch_all("""
        SELECT u.*, json_agg(p.*) as posts
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        GROUP BY u.id
    """)
```

---

## 🎯 CLEAN CODE PRINCIPLES

### Single Responsibility — каждый класс/функция делает одно

```python
# ═══════════════════════════════════════════════════════════════════
# ❌ НЕПРАВИЛЬНО — слишком много ответственности
# ═══════════════════════════════════════════════════════════════════

class BadUserService:
    async def create_user(self, data: dict) -> User:
        # Валидация
        if not data.get("email"):
            raise ValueError("Email required")

        # Сохранение в БД
        user = await self.db.execute("INSERT INTO users ...")

        # Отправка email
        await self.send_email(data["email"], "Welcome!")

        # Логирование
        logger.info(f"User created: {data['email']}")

        return user


# ═══════════════════════════════════════════════════════════════════
# ✅ ПРАВИЛЬНО — разделение ответственности
# ═══════════════════════════════════════════════════════════════════

class UserValidator:
    """Validates user data."""

    def validate_create(self, data: dict) -> UserCreate:
        """Validate and return typed data."""
        return UserCreate(**data)


class UserRepository:
    """Handles user persistence."""

    async def create(self, user: UserCreate) -> User:
        """Save user to database."""
        ...

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch user by ID."""
        ...


class EmailService:
    """Handles email sending."""

    async def send_welcome(self, user: User) -> None:
        """Send welcome email to new user."""
        ...


class UserService:
    """Coordinates user operations."""

    def __init__(
        self,
        validator: UserValidator,
        repository: UserRepository,
        email_service: EmailService,
    ) -> None:
        self._validator = validator
        self._repo = repository
        self._email = email_service

    async def create_user(self, data: dict) -> User:
        """Create new user with validation and notifications."""
        validated = self._validator.validate_create(data)
        user = await self._repo.create(validated)
        await self._email.send_welcome(user)
        logger.info("User created", extra={"user_id": user.id})
        return user
```

### Dependency Injection — зависимости передаются извне

```python
# ═══════════════════════════════════════════════════════════════════
# ✅ FastAPI Depends
# ═══════════════════════════════════════════════════════════════════

from fastapi import Depends

async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency for database session."""
    async with async_session_maker() as session:
        yield session


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    """Dependency for user repository."""
    return UserRepository(session)


async def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Dependency for user service."""
    return UserService(repository=repo)


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Get user by ID."""
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
myproject/
├── .env                        # Переменные окружения (НЕ в git!)
├── .env.example                # Пример env файла (в git)
├── .gitignore
├── pyproject.toml              # Poetry/uv dependencies
├── README.md
├── ruff.toml                   # Конфигурация Ruff
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   │
│   ├── core/                   # Ядро приложения
│   │   ├── __init__.py
│   │   ├── config.py           # Settings (Pydantic)
│   │   ├── database.py         # DB connection
│   │   └── security.py         # Auth, tokens
│   │
│   ├── models/                 # SQLAlchemy/DB модели
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── user.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   ├── repositories/           # Работа с БД (data layer)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── user.py
│   │
│   ├── services/               # Бизнес-логика
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependencies
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── users.py
│   │
│   └── utils/                  # Утилиты
│       ├── __init__.py
│       └── logging.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures
    ├── unit/
    │   ├── __init__.py
    │   └── test_user_service.py
    └── integration/
        ├── __init__.py
        └── test_user_api.py
```

---

## 🛠 ИНСТРУМЕНТЫ

### Ruff — единый линтер и форматер (замена black + flake8 + isort)

```toml
# ruff.toml
line-length = 88
target-version = "py311"

[lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate (commented code)
    "RUF",    # Ruff-specific
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[lint.isort]
known-first-party = ["app"]

[format]
quote-style = "double"
indent-style = "space"
```

### Команды

```bash
# Установка
pip install ruff mypy pytest pytest-cov pytest-asyncio

# Или с uv (быстрее)
uv pip install ruff mypy pytest pytest-cov pytest-asyncio

# Форматирование
ruff format .

# Линтинг
ruff check .

# Автоисправление
ruff check --fix .

# Type checking
mypy app

# Тесты с покрытием
pytest --cov=app --cov-report=html --cov-report=term-missing

# Pre-commit (опционально)
pip install pre-commit
pre-commit install
```

### pyproject.toml пример

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.5",
    "sqlalchemy[asyncio]>=2.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.3",
    "mypy>=1.8",
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД КОММИТОМ

```
□ Type hints для ВСЕХ функций и методов
□ Docstrings для публичных функций/классов (Google style)
□ Обработка ошибок с конкретными исключениями
□ Нет print() — только logger
□ Нет хардкоженных секретов
□ SQL только параметризованный
□ Все тесты проходят
□ Coverage ≥ 80%
□ ruff format . (форматирование)
□ ruff check . (линтинг без ошибок)
□ mypy . (типы без ошибок)
□ Нет TODO/FIXME без задач в трекере
□ Commit message осмысленный (conventional commits)
```

---

## 🚀 БЫСТРЫЙ ПРОМПТ ДЛЯ CLAUDE CODE

```
Работаю над Python проектом. Следуй этим правилам:

СТИЛЬ: Google Python Style + PEP8
- Python 3.11+, 88 символов макс
- 4 пробела, snake_case функции, PascalCase классы
- Type hints обязательны: str | None (не Optional)
- Google docstrings: Args, Returns, Raises

СТРУКТУРЫ ДАННЫХ:
- dataclass(slots=True) для простых данных
- Pydantic BaseModel для API/валидации
- StrEnum для строковых констант
- match-case для паттерн-матчинга

ОБЯЗАТЕЛЬНО:
✅ Конкретные исключения (не голый except)
✅ logger с context (extra={}) вместо print
✅ async/await для I/O, asyncio.gather для параллелизма
✅ Context managers (async with)
✅ Параметризованные SQL (:param или ?)
✅ f-strings
✅ pytest + AAA pattern

ЗАПРЕЩЕНО:
❌ import *
❌ Хардкод секретов
❌ Mutable defaults: def f(x=[])
❌ SQL f-strings
❌ Блокирующий код в async
❌ except: pass

ПРИНЦИПЫ:
- Single Responsibility
- Dependency Injection
- Repository pattern для БД
- Comprehensions > loops
```

---

**Версия:** 2.0
**Дата:** 01.12.2025
**Основа:** Google Python Style Guide + PEP8 + Modern Python 3.11+ Best Practices
