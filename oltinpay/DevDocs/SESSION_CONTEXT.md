# Session Context — OltinPay

> **Читай этот файл первым при продолжении работы**

## Текущий статус

**Проект:** OltinPay — Telegram Mini App для торговли токенизированным золотом
**Дата обновления:** 2026-01-25
**Статус:** ✅ MVP Ready

---

## Что готово

### Backend (Phase 2) ✅
- **Auth** — Telegram initData → JWT
- **Users** — CRUD, oltin_id
- **Balances** — 3 счёта (wallet, exchange, staking), 2 валюты (USD, OLTIN)
- **Transfers** — блокчейн переводы (1% fee)
- **Staking** — депозит/вывод (7% APY, 7 дней lock)
- **Exchange** — ордера, orderbook
- **Contacts** — избранные контакты
- **Aylin** — AI помощник (znai-cloud RAG)
- **Alembic** — миграции БД
- **Docker** — api, postgres, redis
- **Tests** — 33 теста ✓

### Frontend (Phase 3) ✅
- **Next.js 16** + TypeScript + Tailwind CSS v3
- **@twa-dev/sdk** — Telegram Mini App SDK
- **Zustand** — state management
- **React Query** — data fetching
- **i18n** — 3 языка (UZ, RU, EN)

**Страницы:**
- `/wallet` — балансы, табы (wallet/exchange/staking)
- `/exchange` — покупка/продажа OLTIN
- `/staking` — стейкинг с APY
- `/profile` — профиль, смена языка
- `/send` — отправка OLTIN
- `/aylin` — AI чат

### Telegram Bot ✅
- **Inline выбор языка** при /start
- **Приветствие** на выбранном языке
- **WebApp кнопки** с параметром ?lang=
- **Команды:** /start, /lang, /help

---

## Деплой

| Сервис | URL | Статус |
|--------|-----|--------|
| API | https://api.oltinpay.com | ✅ Running |
| WebApp | https://app.oltinpay.com | ✅ Running |
| Bot | @Oltin_Paybot | ✅ Running |

### Docker контейнеры
```
server-oltinpay-api-1      Up (healthy)   8000/tcp
server-oltinpay-webapp-1   Up             3000/tcp
server-oltinpay-bot-1      Up
```

---

## Структура проекта

```
/root/server/oltinpay/
├── DevDocs/                    # Документация
│   ├── CLAUDE.md               # Правила разработки
│   ├── SESSION_CONTEXT.md      # Этот файл
│   ├── standards/              # Стандарты кода
│   └── api/ENDPOINTS.md        # API спецификация
│
├── oltinpay-api/               # Backend (FastAPI)
│   ├── src/                    # Модули: auth, users, balances, etc.
│   ├── tests/                  # 33 теста
│   ├── alembic/                # Миграции
│   └── docker-compose.yml
│
├── oltinpay-webapp/            # Frontend (Next.js)
│   ├── src/app/                # Страницы
│   ├── src/components/         # Компоненты
│   ├── src/hooks/              # useTelegram, useTranslation
│   ├── src/lib/                # api.ts, i18n.ts
│   └── src/stores/             # Zustand store
│
└── oltinpay-bot/               # Telegram Bot (aiogram)
    └── bot.py                  # Inline language selection
```

---

## Ключевые решения

### Архитектура
- 3 счёта: Wallet, Exchange, Staking
- 2 валюты: USD, OLTIN
- Блокчейн только для переводов между пользователями
- Торговля и стейкинг — только в БД

### Tokenomics
- Total Supply: 1,000,000 OLTIN
- Стейкинг: 7% APY, 7 дней lock

### Комиссии
- Переводы: 1% (мин 0.05 USD)
- Биржа: 0.1%
- Между своими счетами: бесплатно

### i18n
- Выбор языка в боте (inline buttons)
- Язык передаётся в Mini App через URL param
- Поддержка: UZ, RU, EN

---

## Следующие шаги

- [ ] Интеграция с реальным API (убрать mock данные)
- [ ] Подключение блокчейна (zkSync Era)
- [ ] Настройка znai-cloud для Aylin
- [ ] Landing page (oltinpay.com)
- [ ] E2E тестирование

---

## Команды для разработки

```bash
# Подключение к серверу
ssh oltinkey

# Логи
docker logs -f server-oltinpay-api-1
docker logs -f server-oltinpay-bot-1

# Пересборка
cd ~/server
docker compose build oltinpay-api oltinpay-webapp oltinpay-bot
docker compose up -d oltinpay-api oltinpay-webapp oltinpay-bot

# Тесты
cd ~/server/oltinpay/oltinpay-api
pytest -v
```
