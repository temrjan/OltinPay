# Standards Index

> Карта стандартов: какой файл читать для какого стека

## Быстрый поиск

| Стек / Задача | Файлы для чтения |
|---------------|------------------|
| **Python** | `python.md` |
| **FastAPI** | `fastapi.md` + `python.md` |
| **TypeScript** | `typescript.md` |
| **React / Next.js** | `react.md` + `typescript.md` |
| **Express.js** | `express.md` + `typescript.md` |
| **PostgreSQL** | `postgresql.md` |
| **Telegram Bot** | `telegram-bot.md` |
| **Telegram MiniApp** | `telegram-miniapp.md` |
| **DevOps / Deploy** | `devops.md` |
| **RAG / Embeddings** | `rag.md` |

## Процесс разработки

| Этап | Файл |
|------|------|
| Новый проект | `../playbook/foundation.md` |
| Ежедневная работа | `../playbook/daily.md` |
| Быстрая справка | `../playbook/quick-reference.md` |
| Все правила кратко | `summary.md` |

## Комбинации для OltinPay

### Backend (FastAPI + PostgreSQL)
```
fastapi.md → python.md → postgresql.md
```

### Frontend (React + TypeScript)
```
react.md → typescript.md
```

### Telegram MiniApp
```
telegram-miniapp.md → react.md → typescript.md
```

### Full-stack задача
```
1. playbook/foundation.md (если новая фича)
2. Стандарты по стеку (см. выше)
3. playbook/daily.md (перед коммитом)
```

---

## Файлы в этой папке

| Файл | Размер | Описание |
|------|--------|----------|
| summary.md | ~11 KB | Сводка всех правил |
| python.md | ~49 KB | Python Style Guide |
| fastapi.md | ~25 KB | FastAPI Guide |
| typescript.md | ~48 KB | TypeScript Style Guide |
| react.md | ~52 KB | React Style Guide |
| postgresql.md | ~44 KB | PostgreSQL Guide |
| telegram-bot.md | ~44 KB | Telegram Bot Guide |
| telegram-miniapp.md | ~39 KB | Telegram MiniApp Guide |
| express.md | ~29 KB | Express.js Guide |
| devops.md | ~37 KB | DevOps Guide |
| rag.md | ~37 KB | RAG System Guide |
