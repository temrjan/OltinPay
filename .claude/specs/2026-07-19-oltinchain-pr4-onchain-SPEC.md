# PR-4 — webapp money-path полностью on-chain — СПЕКА (Гейт-1)

По APPROVED-плану (`…pr4-onchain-PLAN.md`) + ратификация Капитана (вариант Б) +
дескоп-решения 2026-07-19. **Код не начинаю до «го».**

## Ратифицированное (вшито, не переоткрываем)
- **Пользователей НЕТ** → мини-апп перестраиваем свободно, без миграции данных;
  **ГЛАВНОЕ — сохранить дизайн** (он хорош): меняем провода, не перерисовываем.
- **Демо-нарратив:** «завёл 100 UZD через Uzcard/Humo (демо-рельса) → купил/
  продал OLTIN → застейкал → вывел» — тонкий фронт поверх готового `/bank/deposits`.
- **F1 escrow ВЫРЕЗАН** (cap прикрывает; §8-окно принято для демо).
- **F2 paymaster** = существующий `OltinPaymaster` (approvalBased: «мы платим газ,
  юзер — малую OLTIN-комиссию»); catch-22 первой покупки решается **дустом OLTIN**
  при демо-депозите.
- **F4 EIP-191 ВЫРЕЗАН → прод-хардненинг** (кошелёк self-gen, 0 юзеров).
- **НОВОЕ (Капитан 2026-07-19): стейкинг В СКОУПЕ** (§8-отсрочка снята) +
  **Ассистент (aylin) прячется в демо-сборке** (API-роутер не трогаем).

## 🔬 Research-пробы 4a — УЖЕ ОТВЕЧЕНЫ (2026-07-19, read-only)
1. **Staking-биндинг:** live `eth_call OltinStaking(0x63e537…).oltin()` →
   `0x4a56b78…4347` = **V2-OLTIN**. Биндинг `immutable` (`OltinStaking.sol:32,81-83`)
   → **редеплой под V3 обязателен**. Механика совместима как есть: stake/unstake/
   claim = чистый ERC20 `transferFrom/transfer` (`:97,131,150`), rewardPool
   **фандится** (`fundRewardPool :183-185`), НЕ минтит → ролей на V3 не нужно,
   «Exchange = sole minter» цел.
2. **Paymaster:** не задеплоен (DEPLOYMENTS.md без адреса); конструктор берёт
   токен → деплоим `OltinPaymaster(V3_OLTIN)`; скрипт `scripts/deployPaymaster.ts`
   есть (обновить адрес). ⚠️ Контракт **впервые** пойдёт под наши гейты (PR-1
   флот его не ревьюил) — держит ETH и оплачивает газ → в 4a обязателен
   security-ревью паймастера.

## Суб-стадия 4a — контракты/деплой (Solidity-код НЕ меняется)
- Деплой `OltinPaymaster(V3_OLTIN)` + фандинг ETH (ключ деплоера — Капитан, как
  PR-1; Node 20). Обновить `scripts/deployPaymaster.ts` на V3-адрес.
- Редеплой `OltinStaking(V3_OLTIN)` (скрипт по образцу; адрес → DEPLOYMENTS.md).
- rewardPool-фандинг и OLTIN-запас — ops-шаг 4d (OLTIN добывается только через
  Exchange.buy: депозит UZD → buy → fund).
- Гейт-2: security-ревью `OltinPaymaster.sol` (флот — Ревьюер решает объём;
  деплой-скрипты — как PR #6).
- Приёмка: оба адреса в DEPLOYMENTS.md; paymaster ETH>0; staking.oltin()==V3;
  smoke: gasless tx через paymaster проходит на Sepolia.

## Суб-стадия 4b — API (реконсилятор + выпил DB-ledger)
- **Реконсилятор** (фоновая asyncio-джоба в lifespan, по образцу индексера):
  - RECONCILE-выводы: receipt по `tx_hash` → status==1 → CONFIRMED; окончательно
    dropped (N попыток/возраст) → release в PENDING с логом.
  - Phantom-минты (deposit/welcome/attestation, A′-строки с tx_hash): receipt →
    подтверждён / dropped → пометить и исключить из cap (forward-нота Гейта-2′:
    у mint-строк нет маркера → реконсилятор пере-верифицирует ВСЕ tx_hash).
- **Выпил transfers-DB-ledger:** роутер+сервис `/transfers` (история → уже есть
  `/transactions` из индексера), `balances/db.py`, модель `Balance`, 5
  initial-строк в `users/service.py:49-67`, `OLTIN_PRICE_USD` — снести; alembic
  drop `balances`. Contacts/search не трогаем (не money-path).
- **Дуст OLTIN** при `create_deposit` (fix catch-22): ERC20 **transfer** из
  операционного запаса BANK_OPS (НЕ mint — sole-minter цел), сумма = хватает на
  ~10 комиссий paymaster'а. **MINOR-1 (Гейт-1): дуст наследует A2+B2** — он
  лекарство от catch-22, а не best-effort: идёт под reserve-then-broadcast +
  receipt-check как депозитный mint (дропнутый дуст → первая покупка падает;
  дублированный → двойной расход запаса).
- **MINOR-2 (Гейт-1): grep-гейт перед сносом** — явная приёмка 4b: до удаления
  `Balance`/`balances/db.py` grep-доказательство «других читателей нет» (B1
  solvency-cap и coverage-расчёт НЕ читают Balance); grep чист → тогда снос.
- Приёмка: red→green по каждой ветке реконсилятора (мутации: пометка без
  чейн-проверки → красный); **дуст: fire-and-forget без receipt → красный**
  (мутация MINOR-1); grep-гейт MINOR-2 в отчёте; полная сьюта зелёная;
  Console-смоук не сломан (`/por|/rates|/bank/*` не тронуты).

## Суб-стадия 4c — webapp (money-path на viem, дизайн сохранить)
- **MINOR-3 (Гейт-1): ПЕРВЫЙ шаг 4c — дешёвая проба viem×paymaster** (до
  постройки money-path, по образцу staking-пробы 4a): точная сигнатура
  `getApprovalBasedPaymasterInput({token, minAllowance, innerInput})` + отправка
  EIP-712 (type 0x71) tx против УСТАНОВЛЕННОЙ версии viem — доказать одной
  smoke-tx на Sepolia, не догадкой из памяти. Money-path строится только после
  зелёной пробы.
- `contracts.ts` → V3-стек: OLTIN/UZD/Exchange/ReserveAttestor + новые
  PAYMASTER/STAKING адреса; ABI дополнить (Exchange.buy/sell, staking, approve).
- **Все write-tx client-signed** (HDAccount есть) **через paymaster** (zksync
  EIP-712 type 0x71, viem zksync-extension, approvalBased-параметры):
  - Exchange-экран: `/quote` (существующий) → `approve(UZD)` + `Exchange.buy
    (uzdIn, minOltinOut)`; sell зеркально. Мёртвые `/exchange/*`-методы из
    api.ts — снести.
  - Send-экран: `OLTIN.transfer` (+UZD.transfer, если экран поддерживает выбор
    токена — сохранить текущий UX-дизайн).
  - **Staking-экран:** `approve` + `stake(amount)`, `unstake(amount)`, `claim()`
    — на НОВЫЙ адрес; отображение лотов/наград — уже on-chain read (`/balances`).
  - Withdraw: заявка через существующий `/withdrawals` (burn — банк-стороной,
    escrow вырезан).
- **Демо-Uzcard/Humo:** экран пополнения поверх `/deposits`-intent (M3-эндпоинт):
  выбор Uzcard/Humo → intent → реквизиты/«ожидание банка» → poll `/balances`.
  Подтверждение — оператором в Console (см. открытый вопрос Q1).
- **Ассистент спрятан ФЛАГОМ сборки** (NIT-1 принят: env-флаг, не удаление кода
  — обратимо после конкурса, меньше диф; API aylin не трогаем).
- Wallet-экран → новая схема `/balances` (wei-поля); история → `/transactions`;
  optimistic-UI → `waitForTransactionReceipt` → revert = откат + тост (B2-урок
  на клиенте).
- **CI:** добавить test-джоб (vitest) в `webapp.yml` + первые юнит/компонент
  тесты money-path (см. тест-план).
- Приёмка: полный happy-path на Sepolia через UI (депозит-демо → buy → stake →
  unstake → sell → transfer → withdraw-заявка), дизайн визуально прежний,
  ассистента нет, lint/typecheck/build/test зелёные.

## Суб-стадия 4d — ops cutover (7demo, по разведанному плану)
1. `/opt/oltinpay` git-pull до main (с PR-4); `.env` — PR-2/PR-4 переменные
   (роли, HMAC, адреса V3+paymaster+staking, RPC; `--workers 1` явно).
2. Свап: `docker rm -f oltinpay-api oltinpay-webapp` (старые) → `compose up`
   новые (alias тот же — Caddy не трогаем). Откат = поднять старые (секунды).
3. Seed: аттестация резерва; начальный `/fx`; keeper-xau; UZD-трежери Exchange;
   операционный OLTIN-запас BANK_OPS (депозит→buy) → дуст-резерв + rewardPool.
4. Console: контейнер на 7demo + Caddy-блок `console.oltinpay.com` (Q2) с
   `CONSOLE_OPERATOR_PASSWORD` ≥24 симв (деплой-инвариант Гейта-2 PR-3).
5. Смоук: `/por` 200; Console-«гвоздь» (снизить аттестацию → coverage падает);
   webapp happy-path; скриншоты в отчёт.

## Не входит
Mainnet; кастодиан/лицензия; multi-asset; native-mobile; ИИ (прячем, не строим);
escrow (вырезан); EIP-191 (прод); Exchange/V3-изменения; редизайн UI.

## Чтимое
Non-custodial; A1 single-writer (серверные роли); A2; B2 (сервер) /
waitForReceipt (клиент); Дизайн-Б гард; индексер-поллер; без AI-подписей;
red→green мутации; сохранить дизайн webapp.

## Тест-план (скелет; red-мутации на каждую ветку)
- 4a: smoke-скрипт paymaster-gasless tx; staking.oltin()==V3 (деплой-чек).
- 4b: реконсилятор ×3 ветки (RECONCILE→CONFIRMED / dropped→release /
  phantom→settle; мутация: без чейн-проверки → красный); дуст-transfer при
  депозите (мутация: mint вместо transfer → красный/ролевой отказ); выпил — вся
  сьюта без осиротевших импортов.
- 4c (vitest): calldata buy/sell (minOut из quote), transfer, stake/unstake;
  paymaster-поля в tx; revert→UI-откат; новая балансовая схема; «ассистент
  отсутствует в демо-сборке» (снапшот меню).
- 4d: смоук-чеклист + скриншоты (не автотест).

## Открытые вопросы (Гейт-1)
1. **Q1 РЕШЕНО (Капитан «го, оба (а)» 2026-07-19):** демо-депозит подтверждает
   оператор в Console (реалистичный банк-флоу, ноль нового API).
2. **Q2 РЕШЕНО (Капитан, там же):** Console — контейнер на 7demo +
   `console.oltinpay.com` (один Caddy, без внешней зависимости).
3. **Q3 РЕШЕНО (Ревьюер):** полный флот security-weighted на
   `OltinPaymaster.sol` на Гейте-2 4a. Модель угроз флота: (1) дренаж ETH
   недо-ценой fee (fee ≥ реальной стоимости газа?); (2) неограниченное
   спонсорство (allowlist target-контрактов?); (3) reentrancy/переплата в
   postTransaction-refund; (4) approvalBased-only + пиннинг fee-токена;
   (5) атомарность отказа validateAndPay. Deploy-скрипты — как PR #6.

**Гейт-1: APPROVED WITH NITS (2026-07-19).** MINOR-1/2/3 вшиты выше; NIT-1
принят (флаг сборки); NIT-2 (watermark-колонка verified для реконсилятора,
O(all-mints)→прод) — backlog forward-айтем.
**Стоп-условие:** код 4a — после Q1/Q2 + «го» Капитана.
