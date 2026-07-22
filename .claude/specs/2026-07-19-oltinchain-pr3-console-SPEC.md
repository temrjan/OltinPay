# PR-3 Console — СПЕКА (Гейт-1)

Спека по одобренному плану (`2026-07-19-oltinchain-pr3-console-PLAN.md`). Все
архитектурные развилки ратифицированы: **E1** новый Console-app, **E2** серверная
HMAC-подпись, **E3** demo-гейт оператора, **E4** чистый деплой PR-2 API. **Код не
начинаю до «го».**

## Цель
Публичный PoR-Dashboard (live покрытие резерва и mint-cap) + операторская Bank
Panel, из которой на глазах меняются резерв/цены/операции — и дашборд реагирует в
реальном времени. «Гвоздь»: снизить аттестацию → coverage/cap падают вживую.

## Архитектура (locked)
- **E1:** новое приложение `oltinpay/oltinpay-console` (Next.js, app-router,
  server runtime — НЕ статический export, т.к. нужны server route handlers).
- **E2:** Bank Panel вызывает **Next.js route handlers / server actions**,
  которые держат `BANK_HMAC_SECRET` в server-env, подписывают
  `HMAC-SHA256(secret, body||ts||nonce)` и форвардят на API. Секрет в клиентский
  бандл не попадает (критерий приёмки — проверить сборкой).
- **E3:** `/bank`-роуты гейтятся серверным operator-паролем (`CONSOLE_OPERATOR_PASSWORD`,
  server-env); проверка на серверном слое (route handler / middleware), НЕ в
  клиенте. Пароль нетривиальный.
- **E4:** см. раздел «Prerequisite» — деплой живого стека (критический путь).

## 🔴 Prerequisite — live demo stack (E4, критический путь)
Дашборд читает live-эндпоинты; они должны быть **задеплоены и достижимы**, иначе
«гвоздя» нет. Это НЕ часть Console-кода, но блокер демо. Параллельный трек
(я пишу деплой-конфиг, Капитан держит секреты/доступ):
1. **PR-2 API задеплоен** на достижимый HTTPS-хост, **single-worker** — явно
   `WEB_CONCURRENCY=1` / `--workers 1`, задокументировать почему: инвариант A1
   SignerPool (ровно один писатель на ключ) И in-process replay-guard nonce-стора
   HMAC ломаются при мульти-воркере. С Postgres + env-ключами ролей
   (`KEY_BANK_OPS/RESERVE/UZS`, `BANK_HMAC_SECRET`, адреса контрактов V3 Sepolia).
   **CORS/same-origin (замечание Ревьюера #1):** публичный дашборд поллит
   cross-origin — либо `CORS_ORIGINS_STR` включает Console-origin, либо (реком)
   same-origin proxy (см. Public Dashboard). Env-конфиг, не backend-код.
2. **keeper-xau** запущен (свежий XAU/USD, иначе `/rates` протухает по F16-окну).
3. **Начальный `/fx` (UZS)** запощен (через Bank Panel или разово) — иначе цена
   OLTIN не считается.
4. **Аттестация резерва** запощена (grams>0) — иначе `coverage_ratio=null`
   (supply может быть 0). UZD-трежери засеян для confirm/withdraw-демо.
Хост-платформа (Railway/Fly/VPS-контейнер) — ops-под-решение Капитана в рамках
«чистый деплой»; требования: HTTPS, Postgres, single-worker, env-секреты.
5. **Console-деплой (Vercel):** серверные env `API_URL`, `BANK_HMAC_SECRET`,
   `CONSOLE_OPERATOR_PASSWORD`. **Деплой-инвариант (митигация minor'а Гейта-2 —
   operator-гейт без rate-limit): `CONSOLE_OPERATOR_PASSWORD` ≥24 случайных
   символа** (`openssl rand -base64 24`). Опц.: Vercel deployment-protection на
   `/bank`.

## Скоуп PR (Console-код)
### 1. Public PoR Dashboard (`/`, без auth)
Источник — публичные эндпоинты (существуют, backend не меняется):
- `GET /por` → coverage_ratio, reserve_grams (= mint-cap, 1 OLTIN=1г),
  oltin_supply, reserve_updated_at (индикатор свежести), адреса контрактов.
- `GET /rates` → XAU/USD, UZS/USD, oltin_price_uzd.
- `GET /por/history` → лента аттестаций (grams, block, tx, время).

**Доступ (замечание Ревьюера #1 — CORS/same-origin).** Авто-poll идёт из
браузера → cross-origin (Console-домен → API-хост). Рекомендую **same-origin
proxy**: тонкие Next.js route handlers ре-экспонируют эти 3 публичных (без
секрета) чтения — согласуется с серверным паттерном Bank Panel, не требует правки
CORS API («API не трогаю» держится). Альтернатива — `CORS_ORIGINS_STR` API
включает Console-origin (легче для поллинга, но правит API-env). Решение — в
деплой-трек E4.
UI:
- Hero: coverage % + бейдж «Fully backed ≥100%» / «Under-backed <100%».
- **coverage_ratio=null (supply=0)** — обрабатывать явно: показать «No supply
  yet / cap = reserve», НЕ делить на ноль, НЕ показывать NaN (требование
  Ревьюера, чисто UI).
- Свежесть: если `reserve_updated_at` старше порога — визуальный «stale»-флаг.
- Резерв (grams), OLTIN supply, mint-cap, цена OLTIN.
- Лента аттестаций + адреса — с explorer-ссылками (zkSync Sepolia explorer).
- **Авто-poll** каждые ~5–10с → «живой» эффект для «гвоздя».

### 2. Bank Panel (`/bank`, operator-gated, через серверную подпись)
Драйвит существующие HMAC-эндпоинты через серверный слой:
- Post attestation (grams + auditRef) → `/bank/attestations`.
- Post fx (uzsPerUsd) → `/bank/fx`.
- Create deposit (userId|oltinId + amountUzs + bankTxId) → `/bank/deposits`.
- Withdrawals: список pending (`GET /bank/withdrawals?status=pending`) +
  confirm/reject (`/bank/withdrawals/{id}/confirm|reject`).
- Обработка ответов: 200 / 409 (idempotent/уже обработано / reconcile «do not
  retry» — показать понятно) / 401 / 503 (secret не сконфигурен).

### 3. Инфра приложения
package.json, Dockerfile (server runtime), CI-workflow (lint+typecheck+build+
unit), env-конфиг (`NEXT_PUBLIC_API_URL` для публичной части; `API_URL`,
`BANK_HMAC_SECRET`, `CONSOLE_OPERATOR_PASSWORD` — server-only).

### ЯВНО не входит
- Изменения backend/API (не требуются).
- Реальная банковская интеграция; прод-RBAC (E3 demo-гейт); мобильный полиш;
  i18n сверх демо.
- Сам деплой стека — prerequisite-трек (E4), не Console-код.

## Затронутые файлы
- Новое дерево `oltinpay/oltinpay-console/` (Next.js app, server route handlers,
  компоненты дашборда/панели, lib для типов+подписи).
- Новый CI-workflow `console.yml` (lint/typecheck/build/unit).
- Деплой-конфиг API для E4 (отдельный prerequisite-трек — Dockerfile/compose или
  платформенный конфиг под выбранный хост; single-worker).
- **API-код не трогаю.**

## Критерии приёмки — «PR готов, когда…»
- Public Dashboard рендерит live `/por`+`/rates`+`/por/history`, авто-poll,
  explorer-ссылки; открывается без auth; **coverage_ratio=null не ломает UI**.
- Bank Panel через серверную подпись успешно постит аттестацию/fx, создаёт
  депозит, листит и confirm/reject выводы; неверный operator-пароль → отказ на
  сервере.
- **`BANK_HMAC_SECRET` не в клиентском бандле** (grep по `.next`-сборке — чисто).
- **Signing byte-for-byte:** unit-тест сверяет подпись серверного слоя с
  эталонным вектором из `bank/deps.compute_signature` (главный интеграционный
  риск — расхождение конкатенации `body||ts||nonce` или кодировки).
- lint+typecheck+build+unit зелёные.
- Демо-скрипт воспроизводим (после E4): снизить аттестацию → coverage/cap на
  дашборде падают в реальном времени (screenshot в отчёт).

## Definition of Done
merged через Гейт-2 · ветка удалена · lint/typecheck/build+unit зелёные · README
Console (запуск, env, демо-скрипт) · без AI-подписи. E4-prerequisite — отдельный
трек, его DoD (стек живой+достижимый) — условие ДЕМО, не merge Console-кода.

## Тест-план
- **Unit (главный риск):** серверная подпись == `compute_signature` байт-в-байт
  на фикс-векторе (secret, body, ts, nonce); корректные заголовки
  `X-Bank-Signature/Timestamp/Nonce`.
- **Unit:** operator-гейт — неверный/пустой пароль → 401/403 на серверном слое.
- **Component smoke:** Dashboard рендерит мок-`/por` (вкл. кейс
  `coverage_ratio=null`, supply=0 → «no supply»); Bank Panel-формы валидируют
  ввод, зовут server action (мок fetch), показывают 200/409/401.
- **E2E-демо (ручной, отчёт):** снижение аттестации → падение coverage
  (screenshot), после live-стека E4.

## Открытые вопросы
Нет блокирующих — E1/E2/E3/E4 ратифицированы. Хост-платформа E4 (в рамках
«чистый деплой») — ops-под-решение Капитана к моменту деплой-трека; Console-код от
неё не зависит (конфигурируется `API_URL`).
