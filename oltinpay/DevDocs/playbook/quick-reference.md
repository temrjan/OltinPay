# QUICK REFERENCE — Шпаргалка для разработчика

> Краткая выжимка из Части 1 и Части 2

---

## ПЕРЕД НАЧАЛОМ ПРОЕКТА

```
✓ Архитектура: Определи слои (domain/application/infrastructure/presentation)
✓ Style Guide: Настрой black, ruff, mypy в pyproject.toml
✓ Pre-commit: Установи hooks для auto-check
✓ Tests: Создай структуру tests/ и настрой pytest
✓ CI/CD: Напиши GitHub Actions pipeline
✓ Security: Определи auth strategy и secrets management
✓ Docs: README.md, ARCHITECTURE.md, SETUP.md
```

---

## ЕЖЕДНЕВНАЯ РАБОТА

### Morning Routine
```bash
git checkout main && git pull
poetry install
pytest  # Убедись что всё работает
```

### Before Each Commit
```bash
poetry run ruff check . --fix
poetry run mypy .
pytest
git add .
git commit -m "feat(module): description"
```

### Before Creating PR
```bash
# Self-review
git diff main...your-branch

# Run full checks
pre-commit run --all-files
pytest --cov

# Ensure PR < 400 lines
git diff main --stat
```

---

## CODE QUALITY CHECKLIST

```
Naming:
  [ ] Variables: snake_case, descriptive
  [ ] Functions: snake_case, verb_noun (e.g. get_user, calculate_total)
  [ ] Classes: PascalCase, noun (e.g. UserService, PaymentGateway)
  [ ] Constants: UPPER_SNAKE_CASE

Structure:
  [ ] Functions < 20 lines
  [ ] Files < 300 lines
  [ ] No god classes

Type Hints:
  [ ] All function signatures typed
  [ ] Return types specified
  [ ] mypy --strict passes

Tests:
  [ ] Every new feature has tests
  [ ] Coverage > 80%
  [ ] Tests follow AAA pattern (Arrange/Act/Assert)

Security:
  [ ] No secrets in code
  [ ] All inputs validated
  [ ] SQL injection safe
  [ ] Auth checked on protected endpoints

Documentation:
  [ ] Docstrings for public functions
  [ ] Comments explain WHY not WHAT
  [ ] README updated if API changed
```

---

## CODE REVIEW STANDARDS

### As Author:
```
✓ PR description explains why
✓ Self-reviewed before submitting
✓ Tests pass locally
✓ <400 lines of code
✓ Respond to comments within 4 hours
```

### As Reviewer:
```
Check:
  ✓ Design: Does it fit architecture?
  ✓ Functionality: Does it work correctly?
  ✓ Complexity: Can others understand it?
  ✓ Tests: Are they sufficient?
  ✓ Naming: Are names clear?
  ✓ Security: Any vulnerabilities?

Approve if:
  → Code improves overall health
  → Even if not perfect

Respond:
  → First response < 1 day
  → Follow-up < 4 hours
```

---

## COMMON PATTERNS

### Error Handling
```python
# ✓ Good
class DomainException(Exception):
    """Base exception."""
    pass

class InsufficientFundsError(DomainException):
    """Not enough money."""
    pass

try:
    process_payment(amount)
except InsufficientFundsError as e:
    logger.error("payment_failed", error=str(e), user_id=user.id)
    raise HTTPException(400, detail="Insufficient funds")
```

### Input Validation
```python
from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=1_000_000)
    currency: str = Field(min_length=3, max_length=3)
    user_id: int = Field(gt=0)
```

### Logging
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "payment_processed",
    user_id=123,
    amount="10000.00",
    transaction_id="txn_abc",
    duration_ms=150
)
```

### Database Query
```python
# ✓ Good: Eager loading
users = session.query(User).options(
    selectinload(User.orders)
).filter(User.active == True).all()

# ✗ Bad: N+1 queries
users = session.query(User).all()
for u in users:
    print(u.orders)  # Query каждый раз!
```

---

## SECURITY CHECKLIST

### Fintech Specific:
```
✓ Telegram initData validation (HMAC-SHA256)
✓ JWT tokens с short TTL (15-30 min)
✓ Password hashing (bcrypt/argon2)
✓ Input validation (Pydantic strict)
✓ SQL injection prevention (ORM only)
✓ HTTPS enforced
✓ Rate limiting на auth endpoints
✓ Audit logging для financial operations
✓ Encryption at rest (AES-256)
✓ No PII in logs
```

---

## PERFORMANCE TIPS

```
✓ Database:
  - Connection pooling
  - Eager loading для relationships
  - Index на search/filter columns

✓ API:
  - Async/await everywhere
  - Response caching (Redis)
  - Pagination для списков

✓ Code:
  - Avoid N+1 queries
  - Use lru_cache для expensive functions
  - Batch operations где возможно
```

---

## TESTING PATTERNS

```python
# Unit Test
def test_calculate_discount():
    # Given
    price = Decimal("100.00")
    discount_percent = Decimal("20")

    # When
    result = calculate_discount(price, discount_percent)

    # Then
    assert result == Decimal("20.00")

# Integration Test
@pytest.mark.integration
async def test_create_user_api(client, db):
    # Given
    payload = {"email": "test@example.com", "password": "secure123"}

    # When
    response = await client.post("/api/users", json=payload)

    # Then
    assert response.status_code == 201
    user = db.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
```

---

## GIT WORKFLOW

```bash
# Feature branch
git checkout -b feature/ISSUE-123-description

# Regular commits
git commit -m "feat(payment): add Multicard integration"

# Before PR
git rebase main
git push origin feature/ISSUE-123-description

# After approval
git checkout main
git merge --squash feature/ISSUE-123-description
git push origin main
git branch -D feature/ISSUE-123-description
```

---

## COMMIT MESSAGE FORMAT

```
<type>(<scope>): <subject>

Types:
  feat:     New feature
  fix:      Bug fix
  refactor: Code refactor
  test:     Add tests
  docs:     Documentation
  chore:    Maintenance

Examples:
  feat(auth): implement JWT token refresh
  fix(payment): validate amount before processing
  refactor(user): extract KYC logic to service
  test(payment): add integration tests
```

---

## DEBUGGING WORKFLOW

```
1. Reproduce → Write failing test
2. Add logs → Structured logging
3. Hypothesis → What could be wrong?
4. Test → Add assertions
5. Fix → Minimal change
6. Verify → All tests pass
7. Prevent → Add regression test
```

---

## PRODUCTIVITY COMMANDS

```bash
# Quick checks
pytest -v                    # Run all tests
pytest tests/unit/           # Run specific tests
pytest --cov --cov-report=html  # Coverage report
ruff check . --fix           # Auto-fix issues
mypy .                       # Type checking

# Git shortcuts
gst    # git status
gco    # git checkout
gcm    # git commit -m
gp     # git push

# Docker (if used)
docker-compose up -d         # Start services
docker-compose logs -f app   # View logs
docker-compose exec app pytest  # Run tests in container
```

---

## КОГДА ЧТО-ТО СЛОМАЛОСЬ В PROD

```
1. Acknowledge (immediately)
   - Сообщи team что работаешь над этим

2. Mitigate (first 15 min)
   - Rollback если недавний deploy
   - Feature flag off если новая фича
   - Scale up если load issue

3. Fix (next hour)
   - Root cause analysis
   - Write fix + test
   - Deploy carefully

4. Post-mortem (next day)
   - Что случилось?
   - Почему не поймали раньше?
   - Action items для prevention
```

---

## ДЛЯ ФИНТЕХ ИНТЕРВЬЮ

**Знай наизусть:**
```
✓ Security: HMAC, JWT, bcrypt, input validation
✓ Database: ACID transactions, indexing, connection pooling
✓ Testing: Unit/Integration/E2E, TDD approach
✓ Architecture: Layered architecture, dependency inversion
✓ Compliance: PCI DSS basics, KYC/AML process
✓ Monitoring: Structured logging, metrics, alerts
✓ Performance: Caching, async/await, N+1 prevention
```

**Готовься объяснить:**
- Как ты обеспечиваешь security в своих проектах?
- Как handle'ишь concurrent transactions?
- Как тестируешь payment integrations?
- Как monitor'ишь production errors?
- Твой подход к code review?

---

## ФИНАЛЬНЫЙ СОВЕТ

**От лучших компаний:**

> **Google**: "Code is read 10x more than written. Write for readability."

> **Netflix**: "Approve PRs that improve code health, not perfect code."

> **Uber**: "Start simple, add complexity only when needed."

> **Stripe**: "High velocity + high quality. Not mutually exclusive."

**Для финтеха:**

> "Code quality = user trust. One breach destroys years of trust."

---

## КУДА СМОТРЕТЬ ДАЛЬШЕ

**Документация:**
- Google Engineering Practices: github.com/google/eng-practices
- Airbnb Style Guide: github.com/airbnb/javascript
- Python PEP 8: peps.python.org/pep-0008/
- FastAPI Best Practices: fastapi.tiangolo.com

**Книги:**
- "Clean Architecture" — Robert Martin
- "Software Engineering at Google"
- "Designing Data-Intensive Applications" — Martin Kleppmann

**Блоги:**
- Netflix Tech Blog: netflixtechblog.com
- Uber Engineering: eng.uber.com
- Stripe Engineering: stripe.com/blog/engineering

---

**Помни:**
```
✓ Начни с простого
✓ Тести всё
✓ Document decisions
✓ Review код внимательно
✓ Learn from mistakes
✓ Improve continuously
```

**И самое важное:**
> "Perfect code doesn't exist. Good enough code with tests и documentation > perfect code without."

Но для финтеха:
> "Good enough = secure, tested, auditable. Non-negotiable."
