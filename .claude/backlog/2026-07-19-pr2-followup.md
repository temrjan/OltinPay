# Backlog: PR-2 Bank API — follow-up (заведён по условию Ревьюера, Гейт-2′)

Гейт-2′ дельты `761dd13` = ✅ ЧИСТО (B1+B2 закрыты, red→green верифицированы Ревьюером
независимо против живого PG). Ни один пункт ниже НЕ блокер — все верифицированы как
follow-up. Заведено, чтобы «не испарилось» (условие аппрува follow-up).

Источник: вердикт Ревьюера Гейта-2′ (2026-07-19) + отчёт
`reports/2026-07-19-oltinchain-pr2-fixround-delta.md`.

## Follow-up PR (после merge PR-2)

| # | Пункт | Приоритет | Владелец | Заметка |
|---|-------|-----------|----------|---------|
| CI | **api-CI-хардненинг** | **высокий** | Ревьюер (предложил, его лана — как PR #4 на контрактах) | `api.yml` гоняет пиненный pytest-список + НЕТ PG-service → новые PR-2-тесты И `test_concurrency_pg` (единственный regression-guard B1) в CI не гоняются ВООБЩЕ. Security-фикс B1 защищён только локально. Добавить: полный `pytest` + PG-service-контейнер (тогда `concurrency_pg` и M2-миграция реально гейтят). Секвенс: вместе с PR-2 или сразу следом, не завесить. |
| B2a | Receipt-wait вне per-key лока | средний | Инженер | **СДЕЛАНО в `f743c8d`** (feature/pr2-followup, Гейт-2 ожидает). Лок = только nonce→sign→broadcast→nonce++; receipt вне лока, httpx-клиент внешним контекстом (об.#2). Red-пруф R4: старая структура → TimeoutError. |
| B2b | Timeout → RECONCILE, не PENDING | **средний-высокий (корректность)** | Инженер | **СДЕЛАНО в `f743c8d`** (Гейт-2 ожидает). `SignerRevertError`→PENDING vs `SignerReceiptTimeout`→`RECONCILE`+tx_hash (терминален). Об.#1: RECONCILE в ОБОИХ cap-фильтрах (red-пруф R1: без него create 200). Реконсилятор → PR-4. |
| DEP | ~~Депозит/welcome double-mint~~ → **phantom-cap residual** | средний (узкий) | PR-4 (реконсилятор) | **double-mint ЗАКРЫТ в `fbcc43f`** (ратификация A→A′, security-blocker 0.82): `create_deposit` + `welcome.claim_welcome_bonus` + `post_attestation` на `SignerReceiptTimeout` держат резерв (row+tx_hash, commit) + Conflict «не ретраить» → ретрай тем же ключом = 409, второго минта нет. Red→green: нейтрализованные хендлеры → все 3 ретрая минтят дважды. **ОСТАЁТСЯ → PR-4:** phantom-cap-половина (депозит посчитан в withdrawable-cap, но mint неподтверждён) + автоматический реконсилятор (сверка row.tx_hash с чейном → подтвердить/освободить). Self-limiting: вывод против фантома → burn ревертит → RECONCILE. **Форвард-нота Ревьюера:** mint-сайты (deposit/welcome/attestation) хранят строку БЕЗ маркера «неподтверждён» (нет status-поля, миграции по A′-скоупу нет) → reconciler ОБЯЗАН либо пере-верифицировать все `tx_hash` против цепи, либо PR-4 добавляет флаг/status на эти таблицы. Withdrawal-сторона проще (есть статус `RECONCILE`). |
| M2 | Тест миграции alembic 004 на PG | средний | Инженер | `upgrade`/`downgrade` против реального PG; сейчас DDL проверяется только через `create_all`, сам скрипт миграции не прогоняется. Зависит от CI-PG-service (CI-пункт). |
| M3 | ~~Тесты `POST /api/v1/deposits`~~ | средний | Инженер | **СДЕЛАНО в `e912dd1`** (feature/pr2-followup-2): `test_deposits.py` — requisites+reference-формат, auth-required, non-positive→422. Мутация-пруф: wrong-prefix/drop-gt=0 → красное. |
| M4 | ~~Edge-тесты HMAC~~ | низкий | Инженер | **СДЕЛАНО в `e912dd1`**: non-int timestamp→401 (не 500), каждый заголовок по отдельности обязателен. Мутация-пруф: drop int-guard/nonce-check → красное. |
| P3 | Indexer batch-upsert | низкий | Инженер | N+1 upsert → `INSERT … ON CONFLICT` батчем + чанкинг холодного старта. |
| CLEAN | 6 пред-существующих сломанных тестов | низкий | — | `_second_user` fixture — на main, НЕ PR-2. Всплывут, когда CI начнёт гонять полную сьюту. В чистку. |

## PR-4 forward-айтемы (из Гейта-1 PR-4, 2026-07-19)

| # | Пункт | Когда |
|---|---|---|
| NIT-2 | Реконсилятор: колонка-watermark `verified` на mint-таблицах (сейчас пере-верифицирует ВСЕ tx_hash за проход — O(all-mints); при 0 юзеров ок) | прод-хардненинг, не PR-4 |
| EIP-191 | Wallet-ownership proof (вырезан из PR-4 ратификацией — кошелёк self-gen, 0 юзеров) | прод-хардненинг |
| Escrow | On-chain escrow вывода (вырезан из PR-4 — cap прикрывает §8-окно) | прод / после конкурса |

## Отложено (не в follow-up-PR)

- **M1 — ownership-proof привязки кошелька (EIP-191/EIP-712 подпись).** Требует
  запиненного `users/*`. Cap (B1) уже покрывает **fund-loss** (burn не уйдёт за
  namesто OltinPay-minted этому юзеру). Остаточный риск = **address-squatting DoS**
  (чужой адрес привязан → его нельзя привязать легитимно). Держим в трекере до
  разморозки `users/*`. Approach A выбран.

## Вне скоупа (заметки)

- Пред-существующие ruff `TC002` в `tests/test_balances_onchain.py` /
  `tests/test_users_wallet.py` — CI линтит только `src/`. Отдельный `chore:`.
- `uv.lock` untracked (пробел из коммита PR-2 `28d6b96`, где менялся `pyproject.toml`).
  Отдельный `chore:`.
