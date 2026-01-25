# ЧАСТЬ 2: ПРОЦЕСС РАБОТЫ — Daily Engineering Practices

> **Источники**: Google Engineering Practices, Netflix, Uber, Airbnb, Microsoft Azure, Fintech Best Practices

**Цель документа**: Практики, которые применяются КАЖДЫЙ ДЕНЬ во время активной разработки.

---

## 1. CODE REVIEW ПРОЦЕСС

### 1.1 Стандарты Code Review (от Google)

**Главный принцип:**
> "In general, reviewers should favor approving a PR once it **definitely improves** overall code health, even if the PR isn't perfect."

**Что проверяет Reviewer:**

```
✓ Design: Хорошо ли спроектирован код?
  - Соответствует архитектуре проекта?
  - Правильные паттерны использованы?
  - Нет ли over-engineering?

✓ Functionality: Код делает то, что автор хотел?
  - Логика корректна?
  - Edge cases покрыты?
  - Error handling адекватный?

✓ Complexity: Может ли другой разработчик понять этот код через полгода?
  - Нет ли излишней сложности?
  - Можно ли упростить?
  - Очевидна ли логика?

✓ Tests: Есть ли правильные тесты?
  - Unit tests добавлены?
  - Coverage достаточный?
  - Тесты хорошо написаны?

✓ Naming: Имена переменных/функций понятны?
  - Self-explanatory names?
  - Следуют conventions?

✓ Comments: Комментарии полезны?
  - Объясняют "why", не "what"
  - Не дублируют код
  - Актуальны

✓ Style: Следует code style guide?
  - PEP 8 / Airbnb style
  - Форматирование единообразно
  - Linter проходит
```

---

### 1.2 Правила для Code Author

**Перед созданием PR:**
```bash
# 1. Self-review
git diff main...feature/your-branch

# 2. Запусти все проверки локально
poetry run ruff check .
poetry run mypy .
poetry run pytest

# 3. Убедись что pre-commit hooks прошли
pre-commit run --all-files
```

**В описании PR:**
```markdown
## Why?
- Зачем нужны эти изменения?
- Какую проблему решают?
- Ссылка на issue/task

## What?
- Краткое описание изменений
- Скриншоты если UI
- Инструкция как тестить

## Technical Details
- Важные архитектурные решения
- Места, где нужна особая внимательность reviewer
```

**Размер PR:**
- **Золотое правило от Google**: <400 строк кода
- Если больше — разбить на несколько PR
- Исключение: автогенерированный код, migrations

---

### 1.3 Скорость Code Review

**Принцип от Google:**
> "We optimize for the speed at which a **team** can produce a product, not for the speed at which an individual can write code."

**Target SLA:**
```
First response:     < 1 business day
Follow-up response: < 4 hours
Complete review:    < 1 business day
```

**Для reviewer:**
- Не прерывай текущую работу немедленно
- Но выдели 30 минут 2-3 раза в день для PR
- Если PR слишком большой — попроси разбить

---

### 1.4 Handling Conflicts в Code Review

**Если не согласен с reviewer комментом:**

```
1. Попытайся понять точку зрения reviewer
   - Может, он прав?
   - Может, твой код непонятен?

2. Объясни свою позицию с аргументами
   - Performance measurements
   - Ссылки на документацию
   - Примеры из production

3. Если consensus не достигнут:
   - Face-to-face обсуждение (или video call)
   - Привлечь Tech Lead
   - Задокументировать решение в ADR

4. НИКОГДА не оставляй PR висеть в спорах
   - Лучше merge с compromise
   - Чем блокировать development
```

**Правило от Google:**
> "Don't let a PR sit around because the author and reviewer can't come to an agreement."

---

## 2. DEVELOPMENT WORKFLOW

### 2.1 Feature Development Process

**Day-to-day workflow:**

```
1. Создай issue/task
   - Опиши требования
   - Acceptance criteria
   - Estimates

2. Создай feature branch
   git checkout -b feature/ISSUE-123-short-description

3. Write failing tests FIRST (TDD)
   - Напиши тест для нового функционала
   - Запусти тест — он должен fail

4. Implement feature
   - Пиши минимальный код для pass теста
   - Refactor для читаемости

5. Self-review before PR
   - git diff main
   - Прочитай свой код как будто это чужой
   - Добавь комментарии где нужно

6. Create PR
   - Заполни template
   - Назначь reviewer
   - Link issue

7. Address review comments
   - Быстро отвечай на комментарии
   - Делай requested changes
   - Push новые коммиты

8. Merge после approval
   - Squash commits (если много мелких)
   - Delete feature branch
   - Close issue
```

---

### 2.2 Daily Code Quality Practices

**Каждое утро:**
```bash
# 1. Pull latest changes
git checkout main
git pull origin main

# 2. Update dependencies (если были изменения)
poetry install

# 3. Run tests
poetry run pytest

# 4. Если есть failing tests — исправь их СРАЗУ
# Не начинай новую работу с broken tests
```

**Перед каждым коммитом:**
```bash
# Проверь что работает
poetry run pytest

# Проверь style
poetry run ruff check .
poetry run mypy .

# Если есть ошибки — исправь
poetry run ruff check . --fix
```

---

### 2.3 Refactoring Practice

**Правило от Netflix:**
> "Leave the codebase better than you found it."

**Постоянный refactoring:**
```
✓ Видишь дублирующийся код? → Extract to function
✓ Функция >20 строк? → Разбей на меньшие
✓ God class >300 строк? → Split responsibilities
✓ Magic numbers? → Extract to constants
✓ Неочевидное имя? → Rename
```

**Отдельные refactoring PRs:**
- Не мешай refactoring с feature changes
- Refactoring PR = только refactoring, 0 logic changes
- Так легче review

---

## 3. TESTING PRACTICES

### 3.1 Test-First Development

**Для каждого нового use case:**

```python
# 1. Напиши тест СНАЧАЛА
def test_user_can_make_payment():
    # Given: user with balance
    user = create_test_user(balance=Decimal("10000"))

    # When: user makes payment
    result = payment_service.process_payment(
        user_id=user.id,
        amount=Decimal("5000")
    )

    # Then: payment successful and balance updated
    assert result.status == PaymentStatus.SUCCESS
    assert user.balance == Decimal("5000")

# 2. Запусти тест — он должен fail
pytest tests/test_payment.py::test_user_can_make_payment

# 3. Implement minimum code для pass
def process_payment(user_id: int, amount: Decimal) -> PaymentResult:
    user = get_user(user_id)
    user.balance -= amount
    save_user(user)
    return PaymentResult(status=PaymentStatus.SUCCESS)

# 4. Запусти тест — он должен pass
# 5. Refactor код для quality
# 6. Re-run tests для уверенности
```

---

### 3.2 Test Quality Standards

**Good Test характеристики:**

```python
# ✓ GOOD TEST
def test_payment_fails_with_insufficient_funds():
    """Payment should fail when user balance is too low."""
    # Given
    user = create_test_user(balance=Decimal("100"))

    # When / Then
    with pytest.raises(InsufficientFundsError):
        payment_service.process_payment(
            user_id=user.id,
            amount=Decimal("200")
        )

    # And: balance unchanged
    assert user.balance == Decimal("100")

# ✗ BAD TEST
def test_payment():
    u = User(1)
    p = Payment(100)
    assert p.process(u) == True  # Что проверяем???
```

**Test naming convention:**
```
Format: test_<what>_<condition>_<expected_result>

Examples:
  test_payment_with_sufficient_funds_succeeds
  test_payment_with_zero_amount_raises_validation_error
  test_user_registration_with_duplicate_email_fails
```

---

### 3.3 Test Coverage Monitoring

**Обязательные метрики:**
```bash
# Запускай с coverage
pytest --cov=app --cov-report=html --cov-report=term

# Минимальный coverage:
# - domain/: 90%
# - application/: 85%
# - overall: 80%
```

**В CI pipeline:**
```yaml
- name: Test with coverage
  run: |
    pytest --cov=app --cov-fail-under=80
```

---

## 4. DEBUGGING & TROUBLESHOOTING

### 4.1 Structured Logging for Debugging

**Good logging practices:**

```python
import structlog

logger = structlog.get_logger()

# ✓ GOOD: Structured, machine-readable
logger.info(
    "payment_processing_started",
    user_id=user.id,
    amount=str(amount),
    payment_method=method,
    request_id=request.id
)

try:
    result = gateway.charge(amount)
    logger.info(
        "payment_successful",
        user_id=user.id,
        transaction_id=result.transaction_id,
        duration_ms=timer.elapsed()
    )
except PaymentGatewayError as e:
    logger.error(
        "payment_failed",
        user_id=user.id,
        error=str(e),
        error_code=e.code,
        duration_ms=timer.elapsed()
    )
    raise

# ✗ BAD: Unstructured, not searchable
print(f"Processing payment for user {user.id}")
```

**Log levels:**
```
DEBUG:   Детальная информация для debugging
INFO:    Важные события (user login, payment processed)
WARNING: Необычные ситуации (retry attempt, slow query)
ERROR:   Ошибки требующие внимания
CRITICAL: System-level failures
```

---

### 4.2 Debugging Workflow

**Systematic approach:**

```
1. Reproduce the bug
   - Напиши failing test
   - Minimal reproducible case

2. Understand the code flow
   - Добавь логи в key points
   - Use debugger breakpoints

3. Form hypothesis
   - Что может быть не так?
   - Какие данные могли вызвать проблему?

4. Test hypothesis
   - Добавь assertions
   - Check intermediate values

5. Fix & verify
   - Исправь проблему
   - Убедись что тест проходит
   - Проверь что не сломал другое

6. Add regression test
   - Напиши тест для этого бага
   - Чтобы не вернулся
```

---

### 4.3 Production Debugging

**Для production issues:**

```python
# Используй correlation IDs
# Каждый request имеет уникальный ID для tracking

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

    # Add to context для всех логов
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id
    )

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

**Debug через logs:**
```bash
# Найди все логи для конкретного request
grep "correlation_id=abc-123" app.log | jq '.'
```

---

## 5. SECURITY PRACTICES

### 5.1 Daily Security Checklist

**Перед каждым PR:**

```
Input Validation:
  [ ] Все user inputs валидируются?
  [ ] Pydantic models с strict=True?
  [ ] No SQL injection vectors?

Authentication:
  [ ] Protected endpoints имеют auth?
  [ ] JWT tokens валидируются?
  [ ] Permissions проверены?

Data Protection:
  [ ] Sensitive data не в logs?
  [ ] Passwords hashed?
  [ ] Secrets не в коде?

Error Handling:
  [ ] No stack traces в production?
  [ ] Error messages не раскрывают структуру?
  [ ] Rate limiting есть?
```

---

### 5.2 Secure Coding Patterns

**Always:**

```python
# ✓ Input validation с Pydantic
from pydantic import BaseModel, Field, validator

class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=1_000_000)
    currency: str = Field(min_length=3, max_length=3)

    @validator('currency')
    def validate_currency(cls, v):
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {v}")
        return v.upper()

# ✓ SQL injection safe
# FastAPI + SQLAlchemy ORM автоматически safe
users = session.query(User).filter(User.email == email).all()

# ✗ NEVER concatenate SQL
# cursor.execute(f"SELECT * FROM users WHERE email='{email}'")

# ✓ Password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

---

### 5.3 Security Code Review

**Extra checks для финтех кода:**

```
Payment Processing:
  [ ] Amount validation (positive, reasonable limits)?
  [ ] Double-spend protection?
  [ ] Transaction idempotency?
  [ ] Audit logging?

User Data:
  [ ] PII encrypted?
  [ ] Access logging?
  [ ] GDPR compliance (data retention)?

API Security:
  [ ] Rate limiting?
  [ ] CORS configured?
  [ ] HTTPS enforced?
  [ ] API versioning?
```

---

## 6. PERFORMANCE OPTIMIZATION

### 6.1 Daily Performance Checks

**Measure before optimize:**

```python
# ✓ Profile slow endpoints
import time

@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    logger.info(
        "request_completed",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=int(duration * 1000)
    )

    return response
```

**Database query optimization:**

```python
# ✗ N+1 query problem
users = session.query(User).all()
for user in users:
    print(user.orders)  # Каждый раз query в БД!

# ✓ Eager loading
users = session.query(User).options(
    selectinload(User.orders)
).all()
for user in users:
    print(user.orders)  # Уже загружено
```

---

### 6.2 Caching Strategies

**Правила кеширования:**

```python
from functools import lru_cache
import redis

# ✓ Function-level cache для дорогих вычислений
@lru_cache(maxsize=128)
def calculate_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    # Expensive API call
    ...

# ✓ Redis для distributed cache
redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def get_user_with_cache(user_id: int) -> User:
    # Try cache first
    cached = redis_client.get(f"user:{user_id}")
    if cached:
        return User.parse_raw(cached)

    # Cache miss — query DB
    user = session.query(User).filter(User.id == user_id).first()
    redis_client.setex(
        f"user:{user_id}",
        3600,  # TTL 1 hour
        user.json()
    )
    return user
```

**Cache invalidation:**
```python
# Инвалидируй при изменении
def update_user(user: User):
    session.commit()
    redis_client.delete(f"user:{user.id}")
```

---

## 7. MONITORING & ALERTS

### 7.1 Metrics to Track Daily

**Application metrics:**
```python
from prometheus_client import Counter, Histogram

# Request counters
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Latency histogram
request_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint']
)

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_latency.labels(
        endpoint=request.url.path
    ).observe(duration)

    return response
```

---

### 7.2 Error Rate Monitoring

**Alert on anomalies:**

```
✓ Track error rate:
  - 5xx errors > 1% → Critical alert
  - 4xx errors > 10% → Warning

✓ Track response time:
  - P95 > 500ms → Warning
  - P99 > 1s → Critical

✓ Track database:
  - Connection pool exhausted → Critical
  - Slow query > 1s → Warning

✓ Track payment gateway:
  - Failure rate > 5% → Critical
  - Timeout > 10s → Critical
```

---

## 8. INCIDENT RESPONSE

### 8.1 When Production Breaks

**Systematic approach:**

```
1. Acknowledge
   - Confirm you're working on it
   - Update status page

2. Triage
   - How many users affected?
   - Revenue impact?
   - Data loss risk?

3. Mitigate
   - Rollback if recent deployment
   - Scale up if capacity issue
   - Feature flag off if new feature

4. Root Cause Analysis
   - What happened?
   - Why did monitoring not catch it?
   - What's the fix?

5. Fix & Deploy
   - Write fix
   - Test thoroughly
   - Deploy with monitoring

6. Post-mortem
   - Write blameless post-mortem
   - Action items для prevention
   - Update runbooks
```

---

### 8.2 Rollback Procedures

**Quick rollback:**

```bash
# Git tags для releases
git tag v1.2.3
git push origin v1.2.3

# Rollback к previous version
git checkout v1.2.2
./deploy.sh production

# Database migrations rollback
alembic downgrade -1
```

**Feature flags для gradual rollout:**
```python
from feature_flags import is_enabled

@app.post("/api/v2/payments")
async def process_payment_v2(request: PaymentRequest):
    if not is_enabled("new_payment_flow", user_id=request.user_id):
        # Use old flow
        return await process_payment_v1(request)

    # New flow for opted-in users
    ...
```

---

## 9. DOCUMENTATION MAINTENANCE

### 9.1 Keep Docs Updated

**Обязательно обновлять при:**

```
Code change → Update docstrings
API change → Update API docs (OpenAPI)
Architecture change → Update ARCHITECTURE.md
Deployment change → Update DEPLOYMENT.md
New dependency → Update README.md
```

**Правило от Microsoft:**
> "Code without documentation is technical debt."

---

### 9.2 ADR (Architecture Decision Records)

**Для важных решений:**

```markdown
# ADR 001: Use PostgreSQL instead of MongoDB

## Status
Accepted

## Context
Нужно выбрать database для payment transactions.

## Decision
Используем PostgreSQL вместо MongoDB.

## Consequences
+ ACID transactions для consistency
+ Strong typing & schema validation
+ Better tooling (pgAdmin, etc.)
- Более сложный scaling horizontal
- Requires migration для schema changes

## Alternatives Considered
- MongoDB: Flexibility, но нет ACID
- MySQL: Similar to Postgres, но менее feature-rich
```

---

## 10. TEAM COLLABORATION

### 10.1 Daily Standups (если команда)

**Format (5-10 min max):**

```
For each person:
1. What did you do yesterday?
2. What will you do today?
3. Any blockers?

Правила:
- Не technical deep-dive
- Blockers решаются after standup
- Асинхронный standup в Slack если удобнее
```

---

### 10.2 Knowledge Sharing

**Weekly practices:**

```
✓ Brown bag sessions
  - 30 min tech talks
  - Share new patterns learned
  - Demo new tools

✓ Code review learning
  - Reviewer объясняет почему комментарий
  - Author учится на feedback

✓ Pair programming (иногда)
  - Для complex features
  - Для onboarding новичков
  - Для knowledge transfer
```

---

## 11. CONTINUOUS IMPROVEMENT

### 11.1 Retrospectives

**After each sprint/month:**

```
What went well?
  ✓ Fast code reviews (avg 2 hours)
  ✓ Zero production bugs

What went wrong?
  ✗ Too large PRs
  ✗ Flaky tests

What to improve?
  → Enforce 400-line PR limit
  → Fix flaky tests this sprint
```

---

### 11.2 Learning from Mistakes

**Blameless culture:**

```
Bug happened → What process failed?
  ✗ Bad: "Developer X wrote bad code"
  ✓ Good: "We need code review checklist for auth"

Incident → How prevent next time?
  ✗ Bad: "Be more careful"
  ✓ Good: "Add integration test for this scenario"
```

---

## 12. PRODUCTIVITY TIPS

### 12.1 Focus Time

**Deep work practices:**

```
✓ Block 2-4 hours для coding (no meetings)
✓ Turn off notifications во время focus
✓ Use Pomodoro (25 min work, 5 min break)
✓ Code reviews в dedicated slots
```

---

### 12.2 Tools & Shortcuts

**Speed up daily work:**

```bash
# Git aliases
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.st status

# Fish/Zsh shortcuts
alias gcm='git commit -m'
alias gp='git push'
alias gt='pytest'
alias gr='poetry run ruff check . --fix'

# IDE shortcuts (PyCharm/VSCode)
Cmd+Shift+T : Find file
Cmd+B       : Go to definition
Cmd+Alt+L   : Reformat code
```

---

## 13. ФИНАЛЬНЫЙ DAILY CHECKLIST

**Каждое утро:**
```
[ ] Pull latest from main
[ ] Run tests locally
[ ] Check CI status
[ ] Review assigned PRs (before lunch)
[ ] Plan today's tasks
```

**Перед каждым PR:**
```
[ ] Self-review changes
[ ] Run linters (ruff, mypy)
[ ] Run tests (pytest)
[ ] Update documentation if needed
[ ] Fill PR template полностью
[ ] Small PR (<400 lines)
```

**Перед концом дня:**
```
[ ] Commit WIP changes
[ ] Respond to PR comments
[ ] Update task status
[ ] Plan tomorrow
```

**Раз в неделю:**
```
[ ] Update dependencies (poetry update)
[ ] Check security advisories
[ ] Review technical debt backlog
[ ] Share knowledge с командой
```

---

## ПРИНЦИПЫ ОТ ЛУЧШИХ КОМПАНИЙ

**Google:**
> "Approving a PR means the code **improves** overall code health, not that it's perfect."

**Netflix:**
> "Context, not control. Give engineers context to make good decisions."

**Uber:**
> "Move fast, but don't break things. Speed with quality."

**Airbnb:**
> "Be a host: leave the codebase better than you found it."

**Stripe:**
> "High velocity with high quality. They're not mutually exclusive."

**Fintech wisdom:**
> "In fintech, trust is earned in months, lost in seconds. Code quality = user trust."

---

## ЧТО ДАЛЬШЕ?

**Для Тимура:**

1. **Immediate action (этот sprint):**
   - Исправь Telegram initData validation в MiStore
   - Настрой pre-commit hooks
   - Добавь integration tests для payment flow

2. **Short-term (1-2 недели):**
   - Внедри structured logging в все проекты
   - Настрой CI/CD с coverage checks
   - Напиши ARCHITECTURE.md для znai.cloud

3. **Medium-term (1-2 месяца):**
   - Refactor к Hexagonal Architecture
   - Полный test coverage >80%
   - Документация для всех API

4. **Для финтех интервью:**
   - Фокус на security practices (section 5)
   - Знать PCI DSS, KYC/AML базово
   - Уметь объяснить audit logging
   - Понимать transaction idempotency

---

**Remember:**
> "Perfect is the enemy of good. Ship iteratively, improve continuously."

Но в финтехе:
> "Good enough is the enemy of users' money. Quality non-negotiable."

Баланс — вот искусство.
