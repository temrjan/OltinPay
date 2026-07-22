# Отчёт: PR-2 follow-up — B2-слайс (receipt handling v2: B2a + B2b + об.#1/#2)

Ветка `feature/pr2-followup` (off main `a1d2d18`), коммит **`f743c8d`**
(6 файлов, +410/−50, без AI-подписи, **НЕ запушен** — жду «чисто»). Спека:
`specs/2026-07-19-pr2-followup-signer-receipt.md` (финализирована с обоими
обязательными добавлениями Ревьюера; A ратифицировано Капитаном).

## Сделано — по пунктам спеки

### B2a — receipt вне per-key лока (+ обязательное #2)
- `signer_pool.send()`: клиент — ВНЕШНИЙ контекст (переживает релиз лока,
  об.#2); под локом только nonce read/init → sign → broadcast → `nonce++`
  (вкл. `_NonceTooLow`-ретрай); `_wait_for_receipt` — после релиза, тем же
  клиентом. Конкурентный send броадкастит nonce+1 во время чужого ожидания.
- Устаревшие docstring-клеймы («exactly ONE in-flight transaction») исправлены
  на «one broadcast at a time; receipt waits overlap».

### B2b — различение исходов
- `SignerRevertError(tx_hash)` — status==0, детерминированный провал →
  generic-handler в confirm: rollback → `PENDING` (ретраябельно, как раньше).
- `SignerReceiptTimeout(tx_hash)` — дедлайн без receipt, исход НЕИЗВЕСТЕН →
  confirm НЕ откатывает: Core-UPDATE `status=RECONCILE` + `tx_hash` → commit →
  409 банку «parked for reconciliation, do not retry». Повторный confirm/reject
  → 409 (терминален до реконсилятора PR-4).
- `WithdrawalStatus.RECONCILE` — новый член (`String(20)`, миграция не нужна);
  инвариант задокументирован в docstring модели (3 пункта, вкл. cap).

### 🔴 Обязательное #1 — RECONCILE в ОБОИХ cap-фильтрах
- `available_to_withdraw`: outstanding = PENDING+CONFIRMED+**RECONCILE**.
- `confirm_withdrawal`: burned = CONFIRMED+**RECONCILE**.
- Закрывает найденную Ревьюером дыру «банк платит 2× фиат за 1 депозит».

## Red→green (все 4 мутации, свежие прогоны)
| Мутация | RED-вывод | GREEN |
|---|---|---|
| R1: RECONCILE убран из обоих cap-фильтров | оба cap-теста FAILED (`assert 200 == 400` — create прошёл) | passed |
| R2: timeout-handler нейтрализован (rollback→PENDING) | parks-тест FAILED (сырой `SignerReceiptTimeout`, статус pending) | passed |
| R3: timeout кидает базовый `SignerError` | timeout-тест FAILED | passed |
| R4: receipt-wait обратно ПОД лок | lock-release-тест FAILED (`TimeoutError` — send#2 висит на локе) | passed |

## Новые тесты (7)
`test_signer_pool`: timeout→`SignerReceiptTimeout`+tx_hash+nonce-advance;
B2a lock-release (детерминированный: pre-held receipt хэша #1, send#2 под
`wait_for(2s)`, нонсы `[0,1]`); revert ужесточён до `SignerRevertError`+tx_hash.
`test_withdrawals`: timeout→RECONCILE+tx_hash+не-re-confirm'абелен (burn 1 раз);
RECONCILE не reject'абелен; revert→PENDING (регрессия); cap/create (об.#1);
cap/confirm (об.#1, `send_via` не вызван, flip откатан).

## Гейты
```
ruff check src/ + 4 тест-файла ……… All checks passed!
mypy src/ ………………………………………… Success: no issues found in 78 source files
pytest ПОЛНАЯ сьюта ……………………… 120 passed, 6 errors
```
6 errors = пред-существующие `_second_user` (test_contacts/test_users, есть на
main, зафиксированы твоим вердиктом, чинятся в твоём CI-чоуре; мои файлы их не
трогают). Математика: 113 (main) + 7 новых = 120. PG-тест B1 (`concurrency_pg`)
зелёный под `TEST_PG_URL` (podman `pr2pg`).

/security-review + /python-review (само-гейты): корректность — timeout-путь
коммитит RECONCILE одной транзакцией (advisory-лок B1 освобождается и на commit,
и на rollback); cap консервативен с обеих сторон; client-lifetime по об.#2.
Замечаний нет.

## Не сделано / отложено (по спеке)
- Реконсилятор (RECONCILE→CONFIRMED/release по tx_hash) → PR-4.
- Депозит/welcome mint-timeout residual → PR-4 (ратифицировано A; backlog `DEP`
  с precondition).
- M2/M3/M4/P3 — следующие слайсы этого же follow-up (M3 теперь разблокирован:
  A выбрано → deposit-тесты без флага).

## Замечено, не трогаю
- Advisory-лок юзера (B1) держится всё время broadcast+receipt-wait в confirm
  (до ~60с на timeout-пути) → конкурентный create того же юзера ждёт на
  `lock_user`. Это ПРЕД-СУЩЕСТВУЮЩЕЕ поведение смерженного PR-2 (send_via и
  раньше был внутри транзакции с локом), B2a его не менял (B2a — про asyncio-лок
  signer'а, не про PG-лок). Если захочешь сузить — отдельная задача (двухфазный
  confirm), не этот слайс.

## Дельта-2: A′ — депозит/welcome/attestation double-mint (коммит `fbcc43f`)
Ратификация A→A′ (твой security-агент, BLOCKER 0.82). Ты назвал 2 сайта — я
нашёл **третий**: `welcome.claim_welcome_bonus` (тот же `except Exception:
rollback` → double-mint бонуса 1000 UZD). Закрыл все три симметрично
withdrawal-хендлеру: на `SignerReceiptTimeout` — keep-reservation (row+`tx_hash`,
commit) + `ConflictException` «do not retry». Без миграции.
- **Затронуто:** `bank/service.py` (create_deposit, post_attestation),
  `welcome/service.py`, `tests/test_bank.py` (+2), `tests/test_welcome.py` (+1).
- **Red→green:** нейтрализовал все 3 хендлера до старого `rollback` → 3 теста
  FAILED (raw `SignerReceiptTimeout`, ретрай минтит второй раз) → восстановил →
  3 passed. Полная сьюта **123 passed** + 6 пред-существующих `_second_user`.
- **Остаётся → PR-4:** phantom-cap-половина (депозит в cap, mint неподтверждён)
  + реконсилятор. Self-limiting (вывод против фантома → burn revert → RECONCILE).

## Вопросы Ревьюеру
Нет. B2-слайс (`f743c8d`) + A′-добавка (`fbcc43f`) готовы к флоту на дельту
(деньги+ключи). Не пушу до «чисто».
