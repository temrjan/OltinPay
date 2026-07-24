# V3.1 — Перевыпуск денежного края (UZD + Exchange) и сид демо-банка

Дата: 2026-07-24 · Инженер · Гейт-1 (план) → после «go»: код/деплой → Гейт-2
Причина: UZD (`0x95b30Be4…`) имеет totalSupply=0 и все роли у потерянного ключа
V1/V2 (`0xa0A7…779e`); `Exchange.uzd` — immutable. Money-path мёртв без
перевыпуска. Решение Капитана: вариант А («go» 24.07). OLTIN, фиды, резерв,
стейкинг НЕ трогаем.

## Цель

Живой money-path под контролем команды: новый UZD (наш деплоер — admin/minter),
новый Exchange (указатели на существующие OLTIN и фиды), спящий минтер (старый
Exchange) закрыт, сид демо-банка выполнен по К-3 (~половина ёмкости, покрытие
~200%), приёмка — пробный buy с проверкой единиц.

## Скоуп

**Входит:**

1. **Деплой-скрипт `contracts/deploy/deployV31.ts`** (hardhat deploy-zksync,
   Node 20):
   - деплой UZD2 (существующий `UZD.sol`, без правок — тот же байткод-контракт);
   - деплой Exchange2(OLTIN, UZD2, XAU_FEED, UZS_FEED, maxAgeXau=3600,
     maxAgeUzs=259200) — параметры идентичны старому;
   - проводка в той же серии: `OLTIN.grantRole(MINTER_ROLE, Exchange2)` →
     **`OLTIN.revokeRole(MINTER_ROLE, старый Exchange 0xc367…)`** (обязательный
     пункт: спящий минтер закрываем, иначе он оживёт при всплытии ключа V1/V2);
   - паймастер (owner = деплоер): `setSponsoredTarget(UZD2, true)`,
     `setSponsoredTarget(Exchange2, true)`, `setSponsoredTarget(старыйUZD, false)`,
     `setSponsoredTarget(старыйExchange, false)`;
   - верификация после каждого шага чтением: `hasRole`, `sponsoredTarget`,
     байткод новых контрактов keccak == локальным артефактам (практика PR-4a′).
2. **Правка `seed-demo.ts`:** адреса (UZD, EXCHANGE) — в env
   (`UZD_ADDRESS`/`EXCHANGE_ADDRESS`, без захардкоженных констант; фиды/OLTIN
   остаются константами — они не меняются); минт UZD2 — деплоером (он minter),
   `KEY_BANK_OPS` из скрипта убирается.
3. **Чек-лист миграции указателей** (исполняется в этом же PR):
   - `oltinpay-webapp/src/lib/contracts.ts` — UZD/Exchange на новые;
   - `oltinpay-api/src/config.py` — дефолты `uzd_contract_address`,
     `exchange_address` на новые;
   - `oltinpay-api/.env.example` — новые адреса;
   - **сервер**: `/opt/oltinchain/.env.oltinpay` — добавить/обновить
     `UZD_CONTRACT_ADDRESS`, `EXCHANGE_ADDRESS` (сейчас их нет — API без
     сингеров и адресов; только эти две строки, К-6/сингеры — не здесь);
     рестарт контейнера `oltinpay-api` (`docker compose up -d oltinpay-api` из
     `/opt/oltinchain`, без down) + health-check 200;
   - `docs/DEPLOYMENTS.md` — секция V3.1: новые адреса, старые помечены retired
     (UZD-сира с supply=0, Exchange-спящий-минтер-revoked);
   - `README.md` — таблица адресов обновлена;
   - исторические доки (`docs/PROGRESS.md`, `docs/HANDOFF.md`, `docs/TODO.md`,
     `docs/PLAN.md`, `contracts/deploy/deployPaymasterFixed.ts`,
     `oltinpay-api/tests/test_signer_pool.py`) — НЕ правим: они описывают прошлое
     состояние; пометка в DEPLOYMENTS снимает двусмысленность.
4. **Сид (после мержа, из main):** `npm run seed:demo` — mint UZD2 (банк 4 млрд,
   клиенты 50/20/10 млн), газ клиентам, **пробный buy 1M UZD с проверкой
   единиц** (дрейф ≤50bps, иначе стоп), основной buy ~3.9 млрд, покупки
   клиентов, пробный sell 1 г, финальная верификация. Приёмка P1-C = пробный
   buy + финальное состояние чтением.

**Явно НЕ входит:** OLTIN/фиды/резерв/стейкинг/окна maxAge; сингеры API
(`KEY_BANK_OPS`, `ADMIN_PRIVATE_KEY`, К-6) — R-1; снятие `MINTER_ROLE` UZD2 с
деплоера в пользу будущего bank-ops — R-1; верификация исходников на эксплорере
(P5-A); правка исторических доков.

## Затронутые файлы

- `contracts/deploy/deployV31.ts` — новый
- `contracts/scripts/seed-demo.ts` — адреса в env, минт деплоером
- `contracts/.env.example` — `UZD_ADDRESS`, `EXCHANGE_ADDRESS` (новые канонич.)
- `oltinpay/oltinpay-webapp/src/lib/contracts.ts`
- `oltinpay/oltinpay-api/src/config.py`, `oltinpay/oltinpay-api/.env.example`
- `docs/DEPLOYMENTS.md`, `README.md`
- сервер: `/opt/oltinchain/.env.oltinpay` (2 строки) + рестарт `oltinpay-api`

## Критерии приёмки

1. Exchange2 задеплоен с идентичными старому параметрами; байткод UZD2/Exchange2
   keccak == локальным артефактам (вывод в отчёте).
2. `hasRole(MINTER, Exchange2)=true`, `hasRole(MINTER, старыйExchange)=false` —
   чтением; `sponsoredTarget` ×4 соответствует проводке — чтением.
3. Сид зелёный: пробный buy прошёл проверку единиц (≤50bps), `totalSupply` ≈
   половина резерва, покрытие ~200%, пробный sell вернул UZD из казны.
4. API после рестарта: health 200; конфиг содержит новые адреса (чтение env
   контейнера, не вывод скрипта).
5. CI зелёный (все 5 воркфлоу, включая api/webapp — указатели не сломали
   сборку/тесты).

## Definition of Done

- PR смержен по зелёному CI, ветка удалена; сид выполнен из main.
- DEPLOYMENTS/README соответствуют цепи; старые адреса помечены retired.
- Отчёт `.claude/reports/2026-07-24-v31-money-edge.md` с доказательствами.

## Тест-план

- Контрактные изменения отсутствуют → новых юнит-тестов не требуется (UZD.sol и
  Exchange.sol покрыты существующими сьютами, CI их прогоняет).
- Проверки — ончейн: keccak байткода, hasRole/sponsoredTarget до/после,
  пробный buy (дрейф ≤50bps), финальное состояние чтением.

## Риски

- zksolc-деплой флаки (известно по P5-A) — Node 20 обязателен (`nvm use 20`).
- Цена дрейфует между шагами сида — minOut 2%, пробный buy ловит семантику.
- Старый UZD/Exchange остаются на цепи (неизбежно, immutable): помечены retired,
  спонсорство паймастера с них снято, минтер отозван — поверхность закрыта.
