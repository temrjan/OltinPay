# PR-2 follow-up — SignerPool receipt handling v2 (B2a + B2b)

**Гейт-1: ФИНАЛИЗИРОВАНА И ОДОБРЕНА.** Вердикт Ревьюера: APPROVED в направлении +
2 обязательных добавления (внесены ниже: §Обязательное-1, §Обязательное-2) +
ратификация A по депозит-симметрии (рекомендация Ревьюера, ратифицировано
Капитаном «го» 2026-07-19). Ветка `feature/pr2-followup` (off `origin/main`
`a1d2d18`). Закрывает B2-residual'ы из Гейта-2′
(`.claude/backlog/2026-07-19-pr2-followup.md`).

## Цель
Сделать обработку receipt в `SignerPool` корректной по состоянию и не душащей
пропускную способность: (a) не держать per-key лок во время ожидания receipt;
(b) на неопределённый исход (timeout) НЕ возвращать вывод в `PENDING` (иначе
протухшая, но позже замайненная tx → повторный confirm → двойной burn) и —
обязательное #1 — считать такой вывод «может-быть-сожжённым» в solvency-cap.

## Контекст (как сейчас)
`NonceManagedSigner.send()` держит `self._lock` на весь `_build_sign_send`,
включая `_wait_for_receipt` (до 60 с). `_wait_for_receipt` на **любой** не-успех
(revert ИЛИ timeout) кидает `SignerError`; `bank.service.confirm_withdrawal`
ловит `except Exception: rollback; raise` → flip `pending→confirmed`
откатывается → вывод снова `PENDING` и **повторно confirm'абелен**. Для revert
(tx детерминированно ничего не сожгла) это верно; для timeout (tx может
замайниться позже) — двойной burn.

## Инвариант RECONCILE (фиксируется в docstring withdrawals/models)
`RECONCILE` = «burn с неопределённым исходом»:
1. **Не re-confirm'абелен и не reject'абелен** — guard `status==PENDING` не пускает.
2. **Считается-как-burned в solvency-cap** (консервативно: неопределённый burn
   трактуем как случившийся) — входит в `outstanding` при create И в `burned`
   при confirm.
3. **Терминален до реконсилятора PR-4**: → `CONFIRMED`, если tx намайнилась
   успешно / → откат (re-pending или reject), если tx дропнута из мемпула.
   Реконсиляция — по сохранённому `tx_hash`.

## Скоуп PR

### 1. B2a — receipt вне per-key лока
Критическая секция под `self._lock` = только nonce read/init → sign → broadcast
→ `nonce++` (включая одиночный `_NonceTooLow`-ресинк-ретрай). После того как
broadcast принят в мемпул и nonce сдвинут — лок отпускается, `_wait_for_receipt`
ждём ВНЕ лока. Конкурентный send #2 может броадкастить nonce+1, пока #1 ждёт
свой receipt; нонсы по-прежнему аллоцируются строго по порядку под локом.

**Обязательное #2 (Ревьюер) — время жизни httpx-клиента.** Клиент обязан
пережить отпускание лока. Структура строго:
```python
async with httpx.AsyncClient(timeout=15.0) as client:   # внешний
    async with self._lock:                              # внутренний: критсекция
        ...nonce → sign → broadcast → nonce++...
    await self._wait_for_receipt(tx_hash, client)       # вне лока, тот же клиент
```
(Инверсия текущего `async with self._lock, httpx.AsyncClient(...)` — иначе
клиент закроется при релизе лока и receipt-wait упадёт.)

### 2. B2b (signer) — различать исходы
Подклассы `SignerError`, оба несут `tx_hash`:
- `SignerRevertError` — receipt получен, `status==0`: **детерминированный** провал
  (ничего не сожжено/сминчено).
- `SignerReceiptTimeout` — дедлайн без receipt: исход **неизвестен** (может
  замайниться позже).
`send()` их НЕ ретраит (в отличие от `_NonceTooLow`).

### 3. B2b (withdrawal) — state-machine
Новый `WithdrawalStatus.RECONCILE = "reconcile"` (колонка `String(20)` без
DB-enum/CHECK — **миграция НЕ нужна**, проверено). В `confirm_withdrawal`:
- `SignerRevertError` → `rollback` (flip назад в `PENDING`; burn не случился) → raise.
- `SignerReceiptTimeout` → **НЕ rollback**: UPDATE `status=RECONCILE` +
  `tx_hash` из исключения → `commit` → ошибка банку «исход неизвестен,
  реконсиляция; не ретраить». Повторный confirm невозможен (guard) → двойной
  burn исключён.
- Прочие исключения — как сейчас (`rollback; raise`).

### 4. 🔴 Обязательное #1 (Ревьюер, crux) — RECONCILE в ОБА cap-фильтра
Без этого B2b сам открывает over-withdrawal: депозит D → вывод D → confirm →
timeout → RECONCILE; `available = D − 0 = D` → юзер создаёт второй вывод D →
банк платит 2× фиат за 1 депозит. Фикс:
- `withdrawals.service.available_to_withdraw`: `outstanding` = sum WHERE status
  IN (`PENDING`, `CONFIRMED`, **`RECONCILE`**).
- `bank.service.confirm_withdrawal`: `burned` = sum WHERE status IN
  (`CONFIRMED`, **`RECONCILE`**).
- Тест: юзер с депозитом D и одним RECONCILE-выводом D не может ни создать, ни
  подтвердить ещё один вывод.

### 5. Тесты (red→green по §1 /testing) — см. тест-план.

### ЯВНО не входит
- Фоновый реконсилятор (сверка `RECONCILE` по `tx_hash` с чейном) → PR-4.
- On-chain escrow-lock вывода (spec §8) → PR-4.
- **Депозит-симметрия** (mint-timeout: rollback освобождает `bank_tx_id` →
  double-mint при ретрае; или phantom-cap при keep-row) — **РАТИФИЦИРОВАНО A**:
  целиком в PR-4 вместе с реконсилятором. Условия A выполняются: residual
  затрекан в backlog с precondition; триггер пере-оценки → B = демо начинает
  гонять реальные банковские ретраи; ставка низкая (UZD — demo-стейблкоин без
  реального бэка; OLTIN-PoR цел). Касается и welcome-минта (тот же путь).
- M2/M3/M4/P3 — отдельные слайсы follow-up.

## Затронутые файлы
- `src/infrastructure/signer_pool.py` — B2a (структура `send`), исключения.
- `src/withdrawals/models.py` — `RECONCILE` + docstring-инвариант (§выше).
- `src/withdrawals/service.py` — `outstanding` += RECONCILE (обязательное #1).
- `src/bank/service.py` — `burned` += RECONCILE (обязательное #1); обработка
  revert/timeout в `confirm_withdrawal`.
- `tests/test_signer_pool.py`, `tests/test_bank.py`, `tests/test_withdrawals.py`.

## Критерии приёмки — «PR готов, когда…»
- Receipt ждётся ВНЕ per-key лока; конкурентный send доказуемо броадкастит
  nonce+1, пока первый ждёт receipt (red: старая структура ловит timeout теста).
- burn-timeout → вывод в `RECONCILE`, `tx_hash` сохранён, повторный confirm →
  Conflict (не второй burn).
- burn-revert → вывод назад в `PENDING`, ничего не сожжено (регрессия текущего).
- **Cap-тест обязательного #1**: RECONCILE-вывод блокирует и create, и confirm
  сверх депозита (red: без RECONCILE в фильтрах оба проходят).
- red→green показан для timeout-ветки и cap-теста.
- ruff/mypy/полная сьюта зелёные локально (PG-тесты под `TEST_PG_URL`).

## Definition of Done
merged в main через Гейт-2 (Ревьюер: флот на дельту — деньги+ключи) · ветка
удалена · тесты+линт зелёные · docstring `withdrawals/models` обновлён
инвариантом RECONCILE (вкл. пункт про cap) · backlog обновлён. Не полагаться на
api-CI для загейчивания, пока Ревьюер не влил CI-хардненинг.

## Тест-план
- `test_signer_pool`:
  1. Timeout: receipt никогда не приходит (стаб отдаёт `null`), укороченные
     `RECEIPT_TIMEOUT_SEC`/`RECEIPT_POLL_SEC` через monkeypatch → 
     `SignerReceiptTimeout` с `tx_hash`; nonce продвинут. RED: базовый
     `SignerError` вместо подкласса.
  2. B2a лок свободен: send#1 паркуется на receipt (стаб держит его receipt
     `null` по флагу), send#2 под `asyncio.wait_for(…, 2s)` обязан завершиться,
     пока #1 ждёт; нонсы `[0, 1]`. RED: старая структура (receipt под локом) →
     send#2 висит на локе → `TimeoutError`.
  3. Revert-тест ужесточить до `SignerRevertError` (регрессия B2).
- `test_bank`:
  4. Confirm + timeout (patch `send_via` → `SignerReceiptTimeout`) → статус
     `reconcile`, `tx_hash` сохранён, повторный confirm → Conflict, burn один
     раз. RED: нейтрализованный handler → статус `pending`, повторный confirm
     жжёт второй раз.
  5. Confirm + revert (`SignerRevertError`) → статус `pending`, burn не записан
     (регрессия текущего поведения).
  6. Cap/confirm (обязательное #1): депозит D + RECONCILE-вывод D (посеян
     напрямую) + PENDING-вывод D → confirm отказывает, `send_via` НЕ вызван.
- `test_withdrawals`:
  7. Cap/create (обязательное #1): депозит D + RECONCILE-вывод D → create D →
     400 «exceeds». RED (6/7): убрать RECONCILE из фильтров.
