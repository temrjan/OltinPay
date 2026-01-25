# OltinPay Development Rules

> Обязательные правила для Claude при работе над проектом OltinPay

---

## CORE RULE — Читать перед любым кодом

**ПЕРЕД написанием ЛЮБОГО кода:**

1. **Определи стек** → посмотри расширения файлов, импорты
2. **Прочитай стандарты** → `~/DevDocs/standards/_INDEX.md` → нужный файл
3. **Пиши код** → следуя прочитанным стандартам
4. **Покажи compliance** → какие правила применил

**Это обязательно. Без исключений.**

---

## WORKFLOW — 6 этапов

```
INTAKE → PLAN → DEVELOP → VERIFY → COMMIT → DEPLOY
```

| Этап | Что делаем |
|------|------------|
| INTAKE | Понять задачу, уточнить требования |
| PLAN | Архитектура, API контракт, разбивка на задачи |
| DEVELOP | Код + тесты по стандартам |
| VERIFY | Тесты, линтинг, ручная проверка |
| COMMIT | Git commit с понятным сообщением |
| DEPLOY | Деплой, проверка в production |

**Не переходи к следующему этапу, пока текущий не завершён.**

---

## STANDARDS PATH

```
~/DevDocs/
├── standards/          ← Стандарты кода
│   └── _INDEX.md      ← Начни здесь
├── playbook/          ← Процесс разработки
└── architecture/      ← Архитектурные решения
```

## STACK → FILES

| Стек | Читать |
|------|--------|
| Python | `~/DevDocs/standards/python.md` |
| FastAPI | `~/DevDocs/standards/fastapi.md` + `python.md` |
| TypeScript | `~/DevDocs/standards/typescript.md` |
| React/Next.js | `~/DevDocs/standards/react.md` + `typescript.md` |
| PostgreSQL | `~/DevDocs/standards/postgresql.md` |
| Telegram Bot | `~/DevDocs/standards/telegram-bot.md` |
| Telegram MiniApp | `~/DevDocs/standards/telegram-miniapp.md` |
| Express.js | `~/DevDocs/standards/express.md` |
| DevOps | `~/DevDocs/standards/devops.md` |
| RAG | `~/DevDocs/standards/rag.md` |
| Новый проект | `~/DevDocs/playbook/foundation.md` |
| Перед коммитом | `~/DevDocs/playbook/daily.md` |

---

## MCP TOOLS

| Tool | Когда использовать |
|------|-------------------|
| **sequential-thinking** | Архитектурные решения, ADR, trade-off анализ |
| **memory** | Сохранение решений проекта между сессиями |
| **playwright** | E2E тесты, визуальное тестирование |

**Встроенные инструменты:**
- `gh` CLI → GitHub (PR, issues, API)
- WebSearch → документация библиотек
- WebFetch → получение веб-страниц

---

## /dev SKILL

```
/dev standards [stack]   — показать стандарты
/dev plan [topic]        — архитектурный анализ
/dev review [file]       — code review
/dev checklist [type]    — чек-листы (commit, security, foundation, daily)
/dev save [key] [value]  — сохранить в memory
/dev recall [key]        — вспомнить из memory
```

---

## COMMIT MESSAGE FORMAT

```
<type>: <short description>

Types: feat, fix, refactor, test, docs, chore
```

| Type | Когда |
|------|-------|
| feat | Новая функциональность |
| fix | Исправление бага |
| refactor | Рефакторинг без изменения поведения |
| test | Добавление тестов |
| docs | Документация |
| chore | Прочее (deps, configs) |

---

## AUTOMATIC BEHAVIORS

| User says | Claude must |
|-----------|-------------|
| "write", "create", "implement", "build" | Check standards BEFORE coding |
| "fix", "debug", "refactor" | Check standards BEFORE changes |
| "design", "architect", "plan" | Use sequential-thinking |
| "review", "check quality" | Run code review against standards |

---

## ANTI-PATTERNS — Не делать

| ❌ Плохо | ✅ Хорошо |
|----------|-----------|
| Код без чтения стандартов | Сначала стандарты, потом код |
| Один большой коммит | Атомарные коммиты по задачам |
| "fix" / "update" в коммите | Понятное описание изменений |
| Тесты потом | Тесты вместе с кодом |
| Secrets в коде | .env файлы |

---

## CHECKLIST — Перед коммитом

- [ ] Код соответствует стандартам из ~/DevDocs/standards/
- [ ] Тесты написаны и проходят
- [ ] Линтинг пройден
- [ ] Type checking пройден
- [ ] Нет secrets в коде
- [ ] Commit message понятный

---

## KEY PRINCIPLES

### Code Quality
- **Readability first**: Code is read 10x more than written
- **No over-engineering**: Start simple, add complexity only when needed
- **Type safety**: No `any` in TypeScript, strict mypy in Python
- **Security first**: Validate all inputs

---

## SERVERS

| Сервер | Подключение | Путь к проекту |
|--------|-------------|----------------|
| oltinkey | `ssh oltinkey` | /root/server/oltinpay/ |

## PROJECT STRUCTURE (OltinPay)

```
/root/server/oltinpay/          ← На сервере oltinkey
├── DevDocs/                    ← Документация
├── oltinpay-api/               ← Backend (FastAPI)
├── oltinpay-dashboard/         ← Admin panel (Next.js)
└── oltinpay-webapp/            ← Client app (Next.js)

~/DevDocs/                      ← Локальная копия документации
```

---

*Качество > Скорость. Быстро написанный плохой код — технический долг с процентами.*
