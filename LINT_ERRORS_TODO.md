# Ошибки линтера для исправления

> Создано: 2026-01-02
> Коммит: 6b7472f

## Как запустить проверки

```bash
cd ~/server

# Запустить все проверки
pre-commit run --all-files

# Только ruff (линтер Python)
ruff check .

# Только mypy (проверка типов)
mypy .

# Автоисправление ruff
ruff check --fix .
```

---

## 1. Ruff - 1 ошибка

### E402: Import not at top of file

**Файл:** `oltinchain-api/app/api/admin/router.py:421`

```python
# Проблема: импорт в середине файла
# === Internal Endpoints for Bots ===
from pydantic import BaseModel  # <-- Ошибка: должен быть вверху
```

**Решение:** Перенести импорт `BaseModel` в начало файла к остальным импортам.

---

## 2. Mypy - 48 ошибок типизации

### Категория A: UUID типы (30+ ошибок)

**Проблема:** SQLAlchemy UUID несовместим с Python uuid.UUID

**Файлы:**
- `oltinchain-api/app/api/wallet/router.py`
- `oltinchain-api/app/api/orders/router.py`
- `oltinchain-api/app/api/orderbook/router.py`
- `oltinchain-api/app/application/services/orderbook_service.py`

**Пример ошибки:**
```
Argument "user_id" has incompatible type "sqlalchemy.sql.sqltypes.UUID[Any]"; expected "uuid.UUID"
```

**Решение:** Добавить cast или изменить тип в сервисах:
```python
from uuid import UUID
from typing import cast

# Вариант 1: cast
user_id = cast(UUID, current_user.id)

# Вариант 2: изменить сигнатуру функции
def get_balances(self, user_id: UUID | Any) -> ...:
```

---

### Категория B: None checks в ботах (10+ ошибок)

**Файлы:**
- `oltinchain-bots-v3/api_client.py`
- `oltinchain-bots-v3/oracle.py`
- `oltinchain-bots-v3/database.py`

**Пример ошибки:**
```
Item "None" of "Any | None" has no attribute "post"
```

**Решение:** Добавить проверки на None:
```python
# До
response = await self._client.post(...)

# После
if self._client is None:
    raise RuntimeError("Client not initialized")
response = await self._client.post(...)
```

---

### Категория C: Return types (5 ошибок)

**Файлы:**
- `oltinchain-bots-v3/oracle.py:40`
- `oltinchain-bots-v3/bot.py:275`

**Пример:**
```
Incompatible return value type (got "Decimal | None", expected "Decimal")
```

**Решение:** Исправить return type или добавить default:
```python
# До
def get_price(self) -> Decimal:
    return self._cached_price  # может быть None

# После
def get_price(self) -> Decimal | None:
    return self._cached_price

# или
def get_price(self) -> Decimal:
    return self._cached_price or Decimal("0")
```

---

## Приоритеты

| Приоритет | Категория | Файлов | Сложность |
|-----------|-----------|--------|-----------|
| P1 | Ruff E402 | 1 | Легко (5 мин) |
| P2 | None checks | 3 | Средне (30 мин) |
| P3 | UUID types | 6 | Много работы (2ч) |
| P3 | Return types | 2 | Средне (15 мин) |

---

## Альтернатива: ослабить проверки

Если не хочется исправлять все, можно настроить `.pre-commit-config.yaml`:

```yaml
# Отключить mypy
- repo: https://github.com/pre-commit/mirrors-mypy
  # rev: ...
  # hooks:
  #   - id: mypy  # закомментировать
```

Или в `pyproject.toml`:
```toml
[tool.mypy]
ignore_errors = true  # игнорировать все ошибки

# или для конкретных файлов:
[[tool.mypy.overrides]]
module = "oltinchain_bots_v3.*"
ignore_errors = true
```

---

## Быстрое исправление P1

```bash
# 1. Открыть файл
nano ~/server/oltinchain-api/app/api/admin/router.py

# 2. Найти строку 421 с "from pydantic import BaseModel"

# 3. Удалить её оттуда

# 4. Добавить в начало файла (к остальным импортам из pydantic)

# 5. Проверить
cd ~/server && ruff check oltinchain-api/app/api/admin/router.py
```

---

## Полный список файлов с ошибками

### API (oltinchain-api/app/api/)
- `admin/router.py` - E402 import
- `wallet/router.py` - UUID types
- `orders/router.py` - UUID types
- `orderbook/router.py` - UUID types
- `ws/manager.py` - untyped functions

### Services (oltinchain-api/app/application/services/)
- `orderbook_service.py` - UUID types

### Bots (oltinchain-bots-v3/)
- `api_client.py` - None checks
- `oracle.py` - None checks, return types
- `database.py` - None checks
- `bot.py` - return types
- `order_queue.py` - untyped functions
- `rebalancer.py` - untyped functions
