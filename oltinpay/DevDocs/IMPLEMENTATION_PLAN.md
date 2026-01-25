# OltinPay Quality System — Реализация

**Дата:** 2026-01-25
**Статус:** ✅ ЗАВЕРШЕНО

---

## 1. Что создано

### 1.1 Структура документов

```
DevDocs/
├── CLAUDE.md                 ← Правила для Claude
├── IMPLEMENTATION_PLAN.md    ← Этот документ
│
├── standards/                ← Стандарты кода (11 файлов, ~413 KB)
│   ├── _INDEX.md            ← Карта стандартов
│   ├── summary.md           ← Сводка всех правил
│   ├── python.md            ← Python (49 KB)
│   ├── fastapi.md           ← FastAPI (25 KB)
│   ├── typescript.md        ← TypeScript (47 KB)
│   ├── react.md             ← React (52 KB)
│   ├── postgresql.md        ← PostgreSQL (43 KB)
│   ├── telegram-bot.md      ← Telegram Bot (44 KB)
│   ├── telegram-miniapp.md  ← MiniApp (39 KB)
│   ├── express.md           ← Express (29 KB)
│   ├── devops.md            ← DevOps (36 KB)
│   └── rag.md               ← RAG (37 KB)
│
├── playbook/                 ← Процесс разработки
│   ├── quick-reference.md   ← Шпаргалка
│   ├── foundation.md        ← Перед началом проекта
│   └── daily.md             ← Ежедневные практики
│
├── architecture/             ← Архитектурные решения
├── api/                      ← API спецификации
├── guides/                   ← Гайды
└── requirements/             ← Требования
```

### 1.2 MCP серверы

| Сервер | Статус | Назначение |
|--------|--------|------------|
| memory | ✅ Connected | Сохранение решений между сессиями |
| sequential-thinking | ✅ Connected | Архитектурный анализ |
| playwright | ✅ Connected | E2E тестирование |

### 1.3 /dev skill

Расположение: `~/.claude/commands/dev.md`

Команды:
- `/dev standards {stack}` — показать стандарты
- `/dev plan {topic}` — архитектурный анализ
- `/dev review {file}` — code review
- `/dev checklist {type}` — чек-листы
- `/dev save {key} {value}` — сохранить решение
- `/dev recall {key}` — вспомнить решение

### 1.4 CLAUDE.md

Расположение: `DevDocs/CLAUDE.md`

Содержит:
- Core Rule — читать стандарты перед кодом
- Workflow — 6 этапов разработки
- Stack → Files mapping
- MCP Tools usage
- Commit message format
- Anti-patterns
- Checklists

---

## 2. Как использовать

### Перед написанием кода

1. Определи стек (Python? TypeScript? React?)
2. Прочитай `DevDocs/standards/_INDEX.md`
3. Прочитай соответствующий файл стандартов
4. Пиши код следуя стандартам
5. Покажи какие правила применил

### Для архитектурных решений

```
/dev plan "описание задачи"
```

Использует sequential-thinking для структурированного анализа.

### Перед коммитом

```
/dev checklist commit
```

### Code review

```
/dev review path/to/file.py
```

---

## 3. Workflow

```
INTAKE → PLAN → DEVELOP → VERIFY → COMMIT → DEPLOY
```

| Этап | Описание | Инструменты |
|------|----------|-------------|
| INTAKE | Понять задачу | - |
| PLAN | Архитектура | sequential-thinking, /dev plan |
| DEVELOP | Код + тесты | standards/, /dev standards |
| VERIFY | Проверка | /dev review, /dev checklist |
| COMMIT | Git | commit message format |
| DEPLOY | Деплой | devops.md |

---

## 4. Пути

| Что | Путь |
|----|------|
| DevDocs | /root/server/oltinpay/DevDocs/ |
| Standards | /root/server/oltinpay/DevDocs/standards/ |
| Playbook | /root/server/oltinpay/DevDocs/playbook/ |
| CLAUDE.md | /root/server/oltinpay/DevDocs/CLAUDE.md |
| /dev skill | ~/.claude/commands/dev.md |
| MCP config | ~/.claude.json |

---

## 5. Изменения от v1.0

| Было | Стало |
|------|-------|
| znai-cloud KB (внешний) | Локальные файлы standards/ |
| 5 MCP серверов | 3 MCP сервера (только нужные) |
| Папка "Dev Standards" | Папка standards/ (без пробелов) |
| Нет индекса | _INDEX.md с картой стандартов |
| CLAUDE.md ~180 строк | CLAUDE.md ~100 строк |

---

*Система готова к использованию.*
