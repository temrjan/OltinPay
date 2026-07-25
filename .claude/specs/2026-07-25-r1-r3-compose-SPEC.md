# R-1…R-3 — Воспроизводимый compose репозитория (вход в переезд)

Дата: 2026-07-25 · Инженер · Гейт-1 (план) → после «go»: код → Гейт-2 (диф)
План: Фаза 2, строка R-1…R-3. R-4 (переключение) — отдельный ops-шаг следом,
с правилом из Ф0-3: **R-4 не выполнен без полного прогона отката сразу после
cutover** (откатились → 200 → накатились обратно).

## Цель

Репозиторный `docker-compose.yml` становится воспроизводимым способом поднять
OLTINPAY-стек из `/opt/oltinpay` (git-driven), вместо ручной сборки в
`/opt/oltinchain`: без своих postgres/redis (есть shared-инфра), с внешними
сетями, с именем проекта `oltinpay-app` (не уронить лендинг `oltinpay`),
с пиннингом зависимостей и честным `.env.example`.

## Три обязательных ответа (бриф Ревьюера)

**(а) Пиннинг зависимостей API.** Сейчас Dockerfile: `pip install --no-cache-dir .`
по `pyproject.toml` с диапазонами `>=` — каждая пересборка (а R-4 пересобирает)
тянет НОВЫЕ транзитивные зависимости и может сломать сборку ровно в момент
переключения прода. Решение: **`uv.lock` в репозиторий + сборка по локфайлу**:
- `uv.lock` уже сгенерирован и проверен локально (`uv lock --check`, 78 пакетов,
  uv 0.11.26) — коммитим;
- Dockerfile: `uv sync --locked --no-dev` (venv внутри образа, CMD через venv);
- в `api.yml` CI добавить шаг `uv lock --check` — дрейф pyproject↔lock ломает
  сборку до продa, а не на проде.
**(б) `oltinpay-bot`.** Есть в репозиторном compose, контейнера на сервере нет
(старый `oltinchain-bots` остановлен). Решение: **compose profile `bot`,
по умолчанию выключен** — `docker compose up -d` его не поднимет, запуск =
осознанный `docker compose --profile bot up -d`. Подъём compose при cutover не
должен заводить новых движущихся частей. Статус живого бота для демо —
вопрос Капитану (не блокирует R-1…R-3).
**(в) `.env.example` — по фактическим ключам живого контейнера** (прочитаны
24.07, значения не печатались): `DATABASE_URL` (shared postgres,
`…@postgres:5432/oltinpay_db`), `REDIS_URL` (shared, db 3), `SECRET_KEY`,
`TELEGRAM_BOT_TOKEN`, `CORS_ORIGINS_STR`, `RAG_SERVICE_URL`,
`RAG_SERVICE_API_KEY`, `UZD_CONTRACT_ADDRESS`, `EXCHANGE_ADDRESS` (V3.1).
Плюс `ADMIN_PRIVATE_KEY=` пустая (К-6, висит). Имя переменной —
`TELEGRAM_BOT_TOKEN` (как у живого), ремап `OLTINPAY_BOT_TOKEN` из compose
убирается.

## Скоуп PR

**Входит:**

1. **`docker-compose.yml` (корневой):**
   - `name: oltinpay-app` (логическая фиксация R-2; ловушка лендинга закрыта);
   - **убрать сервисы `postgres` и `redis` и их volumes** (shared-инфра
     проекта `infra` уже на сети `internal`);
   - `networks.internal` → `external: true` (сеть shared-инфры), `proxy`
     остаётся external;
   - `oltinpay-api`: env `DATABASE_URL`/`REDIS_URL` берутся из `.env` (не
     конструируются в compose), `depends_on` на удалённые сервисы убрать;
     healthcheck и `command: alembic upgrade head && uvicorn` сохранить
     (нужно для R-4);
   - `oltinpay-bot` → `profiles: ["bot"]`;
   - `oltinpay-webapp`: без изменений по сути (прокси-сеть, build args).
2. **`oltinpay-api/Dockerfile`:** сборка по `uv.lock` (см. ответ (а));
   базовый образ `python:3.11-slim` сохранить (requires-python >=3.11 сходится).
3. **`uv.lock`** — закоммитить (сейчас untracked).
4. **`.env.example` (корневой)** — по ответу (в), значения-плейсхолдеры.
5. **CI `api.yml`:** шаг `uv lock --check`.
6. **Доки:** `docs/DEPLOY.md` — абзац о новом способе подъёма (без переписывания
   под R-6: runbook — там).

**Явно НЕ входит:** R-4 (переключение трафика, alembic на проде, три урла),
R-5…R-8, `DEPLOY_*` секреты и push-триггер deploy.yml (R-7), правка deploy.yml
(R-6), webapp на V3 (P3-C), сингеры API (К-6).

## Затронутые файлы

- `docker-compose.yml`
- `oltinpay/oltinpay-api/Dockerfile`
- `oltinpay/oltinpay-api/uv.lock` (новый в гите)
- `.env.example` (корневой)
- `.github/workflows/api.yml` (шаг lock-check)
- `docs/DEPLOY.md` (абзац)

## Критерии приёмки

1. `docker compose config` валиден: проект `oltinpay-app`, нет сервисов
   postgres/redis, `internal` external, бот за профилем (в `config` без
   профиля бота нет).
2. Сборка образа API локально по локфайлу проходит: `docker build
   oltinpay/oltinpay-api` зелёный; `pip freeze` внутри образа == `uv.lock`
   (выборочно 3 пакета версиями).
3. `uv lock --check` зелёный локально и в CI.
4. `.env.example` содержит ровно ключи живого контейнера (+ADMIN_PRIVATE_KEY
   пустая), без значений.
5. CI зелёный (api + console + contracts + webapp на PR).

## Definition of Done

- PR смержен по зелёному CI, ветка удалена.
- Compose из репозитория поднимает стек локально/на сервере из `/opt/oltinpay`
  (проверка подъёма — в R-4, здесь — `config` + сборка).
- Отчёт `.claude/reports/2026-07-25-r1-r3-compose.md`.

## Тест-план

- `docker compose config` (структурные ассерты из критерия 1).
- `docker build` API + smoke `/health` контейнера с заглушечным env
  (без shared-инфры — подъём uvicorn не проверяем, только сборку и старт до
  первой ошибки конфигурации; полный подъём — R-4).
- `uv lock --check`.

## Риски

- `uv sync` в образе тянет `uv` — поставляется бинарём astral (официальный
  установщик образа `ghcr.io/astral-sh/uv` или `pip install uv==<pin>`;
  пин версии uv тоже фиксируем).
- Удаление своих postgres/redis из compose не трогает их на сервере — там они
  не подняты этим compose (shared-инфра отдельная); проверить при R-4, что
  volume pg_data/redis_data не нужны (они пустые — сервисы ни разу не
  поднимались этим стеком на 7demo).
