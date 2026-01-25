# ЧАСТЬ 1: ФУНДАМЕНТ — Стандарты перед началом разработки

> **Источники**: Google Engineering Practices, Airbnb, Microsoft, Netflix, Uber, Python PEP 8, Fintech Security Standards

**Цель документа**: Задать высокие стандарты качества ДО написания первой строки кода. Этот документ — конституция проекта.

---

## 1. АРХИТЕКТУРНЫЕ РЕШЕНИЯ

### 1.1 Архитектурный стиль
**Принцип**: Архитектура должна быть простой, масштабируемой и понятной.

**Обязательно решить ДО начала кодинга:**

```
✓ Monolith или Microservices?
  - Для MVP и малых проектов (<3 разработчиков): MONOLITH
  - Для больших систем с независимыми доменами: MICROSERVICES
  - Правило от Uber/Netflix: "Start with monolith, split when pain is clear"

✓ Layered Architecture (обязательно):
  /domain          # Бизнес-логика, entities, value objects
  /application     # Use cases, services
  /infrastructure  # БД, внешние API, реализации
  /presentation    # FastAPI endpoints, DTO

✓ Dependency Inversion:
  - domain НЕ зависит от infrastructure
  - Используй Protocol/ABC для абстракций
```

**Документ на выходе**: `docs/ARCHITECTURE.md` с диаграммой компонентов

---

### 1.2 Database Schema Design
**Принцип от Google**: "Design for change, not for current requirements"

```
✓ Нормализация до 3NF минимум
✓ Индексы на Foreign Keys и поисковые поля
✓ Migration strategy (Alembic для SQLAlchemy)
✓ Soft deletes для критичных данных (deleted_at nullable timestamp)
✓ Timestamps: created_at, updated_at на всех таблицах
```

**Для финтех проектов дополнительно:**
```
✓ Audit trail таблицы для всех изменений финансовых данных
✓ Immutable transactions — никогда не UPDATE, только INSERT
✓ UUID вместо auto-increment ID для транзакций
```

---

## 2. CODE STYLE & CONVENTIONS

### 2.1 Python Standards (PEP 8 + расширения)

**Обязательные инструменты:**
```bash
pip install ruff mypy black pre-commit
```

**Конфигурация проекта** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "C90"]
ignore = ["E501"]
```

**Style Guide принципы:**
```python
# ✓ GOOD: Descriptive names, type hints
def calculate_total_price(
    items: list[CartItem],
    discount_code: str | None = None
) -> Decimal:
    """Calculate total price with optional discount."""
    ...

# ✗ BAD: Generic names, no types
def calc(data, code=None):
    ...
```

**Naming Conventions (строго):**
```
Variables/Functions:  snake_case
Classes:              PascalCase
Constants:            UPPER_SNAKE_CASE
Private methods:      _leading_underscore
Modules:              lowercase (no underscores if possible)
```

---

### 2.2 JavaScript/TypeScript Standards (если используется)

**Базовый стандарт**: Airbnb JavaScript Style Guide

**Ключевые правила:**
```javascript
// ✓ Use const/let, never var
const userId = getUserId();
let count = 0;

// ✓ Arrow functions для коротких callbacks
items.map(item => item.id);

// ✓ Destructuring
const { name, email } = user;

// ✓ Template literals
const message = `Hello, ${name}!`;
```

---

## 3. TESTING STRATEGY

### 3.1 Testing Pyramid
**Принцип от Google**: "70% unit, 20% integration, 10% e2e"

```
Обязательные уровни тестирования:

1. Unit Tests (pytest)
   - Каждый use case сервис
   - Каждая domain entity method
   - Минимум 80% coverage для domain/application слоев

2. Integration Tests (pytest + testcontainers)
   - API endpoints + database
   - External API mocks
   - Payment gateway интеграции

3. E2E Tests (для критичных флоу)
   - Registration → KYC → First transaction
```

**Структура тестов:**
```
tests/
├── unit/
│   ├── domain/
│   └── application/
├── integration/
│   ├── api/
│   └── infrastructure/
└── e2e/
```

**Правило от Netflix**: "If you can't test it easily, your architecture is wrong"

---

### 3.2 Test-Driven Development (TDD)
**Обязательно для**:
- Payment processing логика
- Authentication/Authorization
- Любая математика (расчеты, конвертация)

```python
# Пиши тест ПЕРЕД кодом
def test_calculate_discount_percentage():
    # Given
    original_price = Decimal("100.00")
    discounted_price = Decimal("75.00")

    # When
    discount = calculate_discount_percentage(original_price, discounted_price)

    # Then
    assert discount == Decimal("25.00")
```

---

## 4. SECURITY FOUNDATION

### 4.1 Security-First Development

**Принципы от финтех индустрии:**

```
✓ НИКОГДА не храни plaintext passwords/secrets
  - Используй bcrypt/argon2 для паролей
  - Secrets в environment variables или secret manager

✓ Input Validation ВЕЗДЕ
  - Pydantic strict mode
  - Never trust user input
  - Validate на уровне DTO перед domain

✓ SQL Injection Protection
  - ТОЛЬКО параметризованные запросы
  - SQLAlchemy ORM или prepared statements
  - НИКОГДА не конкатенировать SQL

✓ Authentication & Authorization
  - JWT tokens с коротким TTL (15-30 min)
  - Refresh tokens в httpOnly cookies
  - RBAC (Role-Based Access Control)

✓ HTTPS Everywhere
  - TLS 1.3 минимум
  - HSTS headers
  - Secure cookies (httpOnly, secure, sameSite)
```

**Для Telegram Mini Apps (твой MiStore):**
```python
# КРИТИЧНО: Проверка initData от Telegram
import hmac
import hashlib
from urllib.parse import parse_qsl

def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """Validate Telegram WebApp initData using HMAC-SHA256."""
    parsed_data = dict(parse_qsl(init_data))
    hash_value = parsed_data.pop("hash", None)

    if not hash_value:
        return False

    # Create data check string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )

    # Generate secret key
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    # Calculate hash
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return calculated_hash == hash_value
```

---

### 4.2 Fintech Compliance (если применимо)

**Обязательные стандарты:**
```
✓ PCI DSS Level 1/2 (если обрабатываешь карты)
  - Никогда не храни CVV
  - Токенизация карточных данных
  - Encrypted storage

✓ KYC/AML Process
  - Identity verification
  - Document validation
  - Risk scoring

✓ GDPR/Data Protection
  - Data minimization
  - Right to be forgotten
  - Encryption at rest and in transit

✓ Audit Logging
  - Все финансовые операции
  - Authentication attempts
  - Data access logs
  - Retention: минимум 7 лет
```

---

## 5. GIT WORKFLOW & BRANCHING

### 5.1 Branching Strategy
**Рекомендация от Microsoft**: Trunk-based development

```
main (production)
  ↓
develop (staging)
  ↓
feature/ISSUE-123-add-payment-gateway
fix/ISSUE-456-fix-auth-bug
```

**Правила:**
```
✓ main всегда deployable
✓ Feature branches короткие (<3 дней работы)
✓ Rebase перед merge в develop
✓ Squash commits при merge в main
```

---

### 5.2 Commit Messages
**Стандарт**: Conventional Commits

```
Format: <type>(<scope>): <subject>

Types:
  feat:     Новая функциональность
  fix:      Исправление бага
  refactor: Рефакторинг без изменения функционала
  test:     Добавление тестов
  docs:     Документация
  chore:    Рутина (dependencies, config)

Examples:
  feat(payment): add Multicard API integration
  fix(auth): validate Telegram initData on backend
  refactor(user): extract KYC logic to separate service
```

---

### 5.3 Pull Request Requirements

**Обязательные элементы PR:**

```markdown
## Description
Brief summary of changes

## Related Issue
Closes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Security Review
- [ ] No secrets in code
- [ ] Input validation added
- [ ] SQL injection safe

## Checklist
- [ ] Code follows style guide
- [ ] Self-reviewed
- [ ] Comments added for complex logic
- [ ] Documentation updated
```

**Правило от Google**: "PRs должны быть <400 строк кода для эффективного ревью"

---

## 6. DOCUMENTATION STANDARDS

### 6.1 Обязательные документы в проекте

```
/docs
├── ARCHITECTURE.md        # Диаграммы, архитектурные решения
├── API.md                 # API спецификация (или auto-generated OpenAPI)
├── SETUP.md               # Как запустить проект локально
├── DEPLOYMENT.md          # Как задеплоить
├── CONTRIBUTING.md        # Правила для контрибьюторов
└── SECURITY.md            # Security policies, reporting vulnerabilities

/README.md                 # Quick start, badges, основная информация
```

---

### 6.2 Code Documentation

**Python Docstrings** (Google style):
```python
def process_payment(
    user_id: int,
    amount: Decimal,
    currency: str = "UZS"
) -> PaymentResult:
    """Process user payment through payment gateway.

    Args:
        user_id: Unique user identifier
        amount: Payment amount (must be positive)
        currency: ISO 4217 currency code (default: UZS)

    Returns:
        PaymentResult with transaction_id and status

    Raises:
        ValueError: If amount is negative or zero
        PaymentGatewayError: If gateway API fails

    Example:
        >>> result = process_payment(123, Decimal("10000.00"))
        >>> result.status
        'success'
    """
    ...
```

**Когда НЕ писать комментарии:**
- Не дублируй очевидное: `i += 1  # increment i` ❌
- Плохой код + комментарий = плохой код. Рефактори вместо комментария

**Когда писать комментарии:**
- WHY, не WHAT: объясняй бизнес-логику, причины решений
- Complex algorithms
- Workarounds для багов в библиотеках
- TODO/FIXME с issue номером

---

## 7. DEPENDENCIES & ENVIRONMENT

### 7.1 Dependency Management

**Python:**
```bash
# Используй poetry или pip-tools
poetry add fastapi
poetry add --group dev pytest mypy

# Обязательно lock dependencies
poetry lock
```

**Правило от Netflix**: "Pin все версии в production"
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.104.1"  # НЕ "^0.104.1"
sqlalchemy = "2.0.23"
```

---

### 7.2 Environment Configuration

**12-Factor App принципы:**
```python
# settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**Обязательные файлы:**
```
.env.example     # Шаблон с пустыми значениями (в git)
.env             # Реальные credentials (в .gitignore)
.env.test        # Для тестов
.env.production  # Production config
```

---

## 8. CI/CD FOUNDATION

### 8.1 Pre-commit Hooks

**Установка:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

**Правило**: Если pre-commit fails, коммит невозможен.

---

### 8.2 CI Pipeline (GitHub Actions / GitLab CI)

**Минимальный pipeline:**
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Lint
        run: |
          poetry run ruff check .
          poetry run mypy .

      - name: Test
        run: poetry run pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 9. OBSERVABILITY SETUP

### 9.1 Structured Logging

**Правило от Uber/Netflix**: "Logs должны быть машиночитаемыми"

```python
import structlog

# Configure в main.py
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Usage
logger.info(
    "payment_processed",
    user_id=user.id,
    amount=str(amount),
    currency=currency,
    transaction_id=transaction.id
)
```

**Output:**
```json
{"event": "payment_processed", "timestamp": "2024-12-23T10:00:00Z",
 "user_id": 123, "amount": "10000.00", "currency": "UZS",
 "transaction_id": "txn_abc123"}
```

---

### 9.2 Metrics & Health Checks

**FastAPI endpoints:**
```python
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}

@app.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Check if app is ready to serve requests."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(503, detail="Database unavailable")
```

---

## 10. PERFORMANCE BASELINES

### 10.1 Performance Targets
**Установи KPI ДО начала разработки:**

```
API Response Time:
  - 95th percentile < 200ms
  - 99th percentile < 500ms

Database Queries:
  - < 50ms для простых SELECT
  - < 200ms для complex JOINs
  - Используй EXPLAIN ANALYZE

Connection Pooling:
  - SQLAlchemy pool_size=10, max_overflow=20
  - Redis connection pool

Async Everywhere:
  - FastAPI async def
  - asyncpg для PostgreSQL
  - aiohttp для external API
```

---

## 11. ERROR HANDLING PATTERNS

### 11.1 Exception Hierarchy

```python
# domain/exceptions.py
class DomainException(Exception):
    """Base for all domain exceptions."""
    pass

class ValidationError(DomainException):
    """Invalid input data."""
    pass

class PaymentFailedError(DomainException):
    """Payment processing failed."""
    pass

class InsufficientFundsError(PaymentFailedError):
    """Not enough money in account."""
    pass
```

**В FastAPI:**
```python
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=400,
        content={"error": exc.__class__.__name__, "detail": str(exc)}
    )
```

---

## 12. CHECKLIST ПЕРЕД НАЧАЛОМ КОДИНГА

```
Архитектура:
  [ ] Архитектурная диаграмма создана
  [ ] Слои определены (domain, application, infrastructure, presentation)
  [ ] Database schema спроектирована
  [ ] API endpoints перечислены

Code Standards:
  [ ] pyproject.toml настроен (black, mypy, ruff)
  [ ] Pre-commit hooks установлены
  [ ] Style guide прочитан командой
  [ ] Naming conventions согласованы

Testing:
  [ ] Тестовая структура создана
  [ ] Pytest + fixtures настроены
  [ ] CI pipeline написан

Security:
  [ ] Authentication strategy определена
  [ ] Secrets management решен (env vars, secret manager)
  [ ] Input validation patterns согласованы
  [ ] Security checklist прочитан

Documentation:
  [ ] README.md написан
  [ ] ARCHITECTURE.md создан
  [ ] SETUP.md для локальной разработки

Git Workflow:
  [ ] Branching strategy выбрана
  [ ] Commit message format согласован
  [ ] PR template создан

Observability:
  [ ] Structured logging настроен
  [ ] Health check endpoints добавлены
  [ ] Metrics определены (что измерять)

Dependencies:
  [ ] Poetry/pip-tools настроен
  [ ] .env.example создан
  [ ] Dependencies pinned
```

---

## ВАЖНЫЕ ПРИНЦИПЫ

**От Google:**
> "Code is read much more often than it is written. Optimize for readability."

**От Netflix:**
> "The primary purpose of code review is to improve overall code health over time."

**От Uber:**
> "Microservices solve organizational problems, not technical ones. Start simple."

**От финтех:**
> "Security is not a feature. It's a foundation."

**Золотое правило:**
> "Если ты не можешь объяснить код новому разработчику за 5 минут — код плохой."

---

**Следующий шаг**: Прочитать ЧАСТЬ 2 про процесс разработки и daily practices.
