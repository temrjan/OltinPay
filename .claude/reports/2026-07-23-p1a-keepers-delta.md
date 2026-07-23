# Дельта-отчёт: P1-A — фикс блокера Гейта-2

Дата: 2026-07-23 · Инженер · ре-ревью (только дельта к `.claude/reports/2026-07-23-p1a-keepers.md`)

## БЛОКЕР — дикое отклонение уходило «сознательным пропуском»: закрыт

**Правка** (`keeper-lib.ts:decidePost`): ветка гарда скачка возвращает
`refuse` (код 1) вместо `skip` (код 2) — всегда, без оглядки на heartbeat.
Гард важнее heartbeat: пересечение покрыто новым тестом.

**Доказательство red→green (правило №0):**

Сначала изменены тесты (ожидание `refuse` + новый тест пересечения), прогон на
неизменённом коде:
```
1) should refuse a wild deviation beyond the jump guard instead of relaying it
2) should refuse a wild deviation even when the heartbeat is due — guard beats heartbeat
21 passing, 2 failing
```
После правки `decidePost`: полная сюита `npm test` → **187 passing** (было 186,
+1 тест пересечения), 0 failing.

**Документы приведены в соответствие:** спека (контракт кодов возврата +
тест-план, строки 5/5a), шапки `keeper-xau.ts` / `keeper-uzs.ts`
(«we skip» → «we refuse (needs a human)»).

## НИТы — закрыты

- `parsePositiveInt`: сообщение «non-negative» при требовании строго
  положительного → переформулировано («not a valid integer»; проверка
  положительности уже имела своё сообщение).
- «4 коммита» в шапке основного отчёта → исправлено на ссылку на эту дельту
  (ветка на момент дельты: 7 коммитов).

## МИНОР — К-8 keyed RPC: записан в план

Строка P1-B дополнена: «завести keyed RPC-провайдер (К-8) — основной путь ни
разу не проверен». Ручной прогон P1-A действительно шёл на публичном
fallback — подтверждаю, в отчёте это было объявлено («Замечено/отложено»).

## Как тестировал

- `npx hardhat test test/keeper.test.ts` — red (2 failing) → green после правки
- `npm test` (полная сюита) → 187 passing
- Поведение на цепи не затронуто: правка меняет только классификацию отказа,
  постed-значения фидов не требуют перевыпуска.

## Файлы дельты

- `contracts/scripts/keeper-lib.ts` — refuse вместо skip; сообщение parsePositiveInt
- `contracts/test/keeper.test.ts` — ожидание refuse + тест пересечения
- `contracts/scripts/keeper-xau.ts`, `keeper-uzs.ts` — шапки
- `.claude/specs/2026-07-23-p1a-keepers-SPEC.md` — коды возврата, тест-план
- `.claude/PLAN-2026-07-23.md` — P1-B: keyed RPC
- `.claude/reports/2026-07-23-p1a-keepers.md` — ссылка на дельту
