# Отчёт (ДЕЛЬТА): PR-2 Bank API — фикс-раунд по Гейту-2

Ветка `feature/pr2-bank-api`. Отвечает на вердикт Ревьюера по `28d6b96` (BLOCKED:
B1, B2 + миноры). Фикс-раунд сделан **вручную по кодексу** (без ультракода, по
распоряжению Капитана). Новый коммит: **`761dd13`** (7 файлов, +325/−22, без
AI-подписи, НЕ запушен — жду «чисто»).

## Сделано — оба блокера закрыты, доказаны red→green (свежие прогоны этой сессии)

### B1 — атомарный solvency-cap (per-user advisory lock)
- Новый `src/infrastructure/db_lock.py::lock_user()` — транзакционный
  `pg_advisory_xact_lock(hashtextextended(cast(:uid AS text), 0))`. Параметризован
  (`:uid`), no-op на не-Postgres (SQLite-сьют). Держится до commit/rollback.
- `withdrawals/service.create_withdrawal`: `lock_user` **до** чтения cap.
- `bank/service.confirm_withdrawal`: `lock_user` **до** flip+cap. Ложный комментарий
  про «serialized behind KEY_BANK_OPS» исправлен (KEY_BANK_OPS сериализует только
  broadcast; race-free даёт именно `lock_user`).
- **Тест переписан на детерминированный** (важно — см. «Отклонения»):
  `tests/test_concurrency_pg.py`. Корутина A паркуется внутри критической секции,
  держа лок; B гонится. С локом B блокируется до commit A → cap-reject; без лока B
  проходит на устаревшем cap.
  - GREEN (реальный лок): **3/3 passed** (~0.76s — подтверждает, что B реально
    висел на локе 0.5s).
  - RED (лок полностью вырезан — `return` в самом начале): **3/3 failed** —
    `AssertionError: second concurrent withdrawal was NOT rejected … (BLOCKER B1
    regressed)`.

### B2 — проверка receipt status==1 для всех ролей
- `signer_pool.NonceManagedSigner._wait_for_receipt()`: после broadcast поллит
  `eth_getTransactionReceipt`, требует `status==1`; revert/timeout → `SignerError`.
  Nonce инкрементится **до** ожидания (reverted-but-mined tx съедает nonce).
  Revert пробрасывается вверх → `except Exception: rollback` откатывает
  резервацию (withdrawal → PENDING / deposit-row удаляется).
- Тест `tests/test_signer_pool.py::test_send_raises_on_reverted_receipt`
  (+ ветка `eth_getTransactionReceipt` в `_RpcStub`, параметр `receipt_status`).
  - RED (проверка receipt вырезана): `Failed: DID NOT RAISE SignerError`.
  - GREEN (с проверкой): passed (в общем прогоне).

### Миноры этого раунда
- **P1**: три per-send RPC-чтения (`gasPrice`/`estimateGas`/`maxPriorityFeePerGas`)
  собраны через `asyncio.gather` — короче удержание per-key лока.
- **P2**: два feed-чтения в `/quote` собраны через `gather` (как в get_por/get_rates).

## Само-ревью (обязательные гейты Ревьюера для Инженера)
- **/testing** (критерий): red→green доказан для обоих блокеров, свежие прогоны выше.
  B1-тест сделан детерминированным, а не timing-флейки.
- **/security-review**: ручной проход по всем 7 файлам дельты — **чисто**. Дельта —
  нетто-улучшение безопасности (закрывает unbounded-burn гонку B1 и
  reverted-burn-as-success B2). Инъекций нет (advisory lock параметризован).
- **/python-review**: correctness/perf/security/readability — без блокеров/ошибок.
  Порядок в `confirm_withdrawal` (lock→flip→cap(sum CONFIRMED)→burn→commit) race-free,
  т.к. `create_withdrawal` под тем же локом держит инвариант pending+confirmed ≤
  deposited; cap на confirm — корректный defense-in-depth backstop. `int(status,16)`
  fail-closed.

## Как тестировал (команды + вывод)
```
env: SECRET_KEY=ci-test-secret DATABASE_URL=…@localhost/test
     TEST_PG_URL=postgresql+asyncpg://test:test@localhost:55432/test  (podman PG 17)

ruff check src/ …………………………………………… All checks passed!
mypy --ignore-missing-imports src/ ………… Success: no issues found in 78 source files
pytest (bank/withdrawals/signer/por/indexer/welcome + concurrency_pg) … 47 passed

B1 red (lock neutered):   3/3 failed  (assert: B1 regressed)
B1 green (lock restored): 3/3 passed
B2 red (receipt dropped): 1 failed    (DID NOT RAISE SignerError)
B2 green (restored):      passed
```

## Не сделано / отложено — предлагаю быстрым follow-up (НЕ в этом коммите)
Сознательный честный разрез: в конце длинной сессии закрыл оба блокера с полным
red→green + P1/P2, а более объёмные тест-миноры вынес, чтобы не жертвовать
качеством. Все — низкий риск, чисто покрытие:
- **M2**: тест миграции 004 на реальном PG (alembic upgrade/downgrade); сейчас DDL
  проверяется только через `create_all`, сам скрипт миграции не прогоняется.
- **M3**: тесты `POST /api/v1/deposits` (authed) — файла `test_deposits.py` нет.
- **M4**: edge-тесты HMAC (`int(timestamp)` на мусоре, одиночные отсутствующие
  заголовки).
- **P3**: indexer N+1 upsert → batch `INSERT … ON CONFLICT` + чанкинг холодного старта.
- **M1** (ownership-proof кошелька): отложен — approach A выбран, требует `users/*`
  (запинен). Пока покрыт cap'ом (burn не может уйти за namesто OltinPay-minted).

## Замечено, не трогаю (вне скоупа)
- Пред-существующие ruff `TC002` в `tests/test_balances_onchain.py` и
  `tests/test_users_wallet.py` — не мои файлы, CI линтит только `src/`. Отдельной
  задачей.
- `uv.lock` — untracked (пробел из коммита PR-2 `28d6b96`, где менялся
  `pyproject.toml`). Вне скоупа фикс-раунда; предлагаю отдельным `chore:`.

## Вопросы Ревьюеру
1. ОК ли принять **детерминированный** B1-тест вместо буквального `gather`
   из спеки? (Причина: `gather`-версия проходила ЗЕЛЁНОЙ даже без лока при удачном
   планировщике — слепое пятно ровно для той регрессии, что надо ловить.)
2. ОК ли вынести M2/M3/M4/P3 быстрым follow-up-PR (все — покрытие, низкий риск)?
