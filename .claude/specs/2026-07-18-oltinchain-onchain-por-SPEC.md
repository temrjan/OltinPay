# СПЕКА (Гейт-1): OltinChain → полностью on-chain PoR-токенизация

> Статус: **СПЕКА на «го».** План APPROVED Ревьюером с обязательными дополнениями — все
> инкорпорированы здесь. Кода нет до «го» Капитана. Порядок: план✔ → ревью✔ → **спека (тут)**
> → «го» → код (PR-1 первым).
> Кресло: Инженер. Репо: `temrjan/OltinPay`, рабочая копия `~/Dev/projects/oltinpay`, HEAD `c371651`.
> Родитель: `2026-07-18-oltinchain-onchain-por-PLAN.md`. Цель-трек: Tech Award FinTech Incubation.
> ИИ в проект НЕ вшивается (решение Капитана). Все факты §2 плана перепроверены; §2 исправлена (ниже).

## 0. Исправления к плану (по ревью)

- **§2 плана была неверна** (finding #3, VERIFIED мной): on-chain серверная подпись УЖЕ существует —
  `config.py:53 admin_private_key: SecretStr|None`; `admin_tx.py:78-134 send_admin_mint` шлёт
  `eth_sendRawTransaction` (EIP-1559 type-2, eth-account). `welcome/service.py` уже минтит UZD
  on-chain. **Следствие:** PR-2 переиспользует `admin_tx.py`, не пишет керер-подпись с нуля →
  оценка PR-2 вниз; но код-путь `admin_tx.py` требует переработки под nonce/ключи (Дизайн-А).
- **NIT #7:** фикс-цена — `transfers/service.py:26` (`OLTIN_PRICE_USD = Decimal("100")`), не :27.

## 1. Цель

Довести OltinChain до **полностью on-chain токенизации на zkSync Sepolia**, где эмиссия
обеспеченного токена (OLTIN, 1 = 1 г золота) программно ограничена аттестованным резервом
(Chainlink-совместимый Proof-of-Reserve / Secure-Mint паттерн), банк подключается стандартным
набором эндпоинтов, а обеспечение и регулирование видны в Console (Bank Panel + публичный PoR
Dashboard). Демонстрируем механизм так, чтобы банк понял «как применить у себя», а регулятор —
доказуемость обеспечения. Инвариант, проверяемый контрактом:

```
totalSupply(OLTIN_V3) ≤ аттестованный_резерв(граммы)   — при каждом mint
```

## 2. Скоуп

**Входит:** контракты OltinTokenV3 (PoR-gated mint, без adminTransfer) + Attestor×3 + Exchange;
Bank Connector API (7) + user (6) + public (4); Console (Bank Panel + PoR Dashboard); перевод
money-path из Postgres в цепь; keeper-скрипты (XAU-релей, курс ЦБ); тесты + красные мутации;
README/docs (EN+RU) с честным позиционированием; чистка лендинга от овер-клейма.

**ЯВНО НЕ входит:** реальное золото/кастодиан/лицензия (прод-фаза/песочница); mainnet-деплой;
`staking`/`aylin`/`contacts` (не трогаем); multi-asset factory; native-mobile; **любые
ИИ-функции**; смена стека лендинга (только чистка текстов); reorg-устойчивый индексер (Дизайн-В §6).

## 3. Архитектура (зафиксирована)

### 3.1 Контракты (Solidity ^0.8.24, hardhat-zksync, деплой zkSync Sepolia 300)

| Контракт | Роль |
|---|---|
| **OltinTokenV3** | ERC20 «1 OLTIN = 1 г». Mint гейтится PoR (Дизайн-Б). `adminTransfer` УДАЛЁН. Роли: **MINTER=только Exchange, PAUSER** (роли BURNER НЕТ). Бёрн — публичный ERC20Burnable `burnFrom` (allowance-gated, non-custodial); функции жечь у произвольного холдера НЕТ (преф-1). `transferFeeBps` хранится/конфигурируется, но в PR-1 к трансферам **не применяется** (dormant — иначе ломает settlement buy/sell; включение с exempt отложено) |
| **Attestor** (1 код × 3 инстанса) | AggregatorV3Interface-совместимый; `postAnswer` под ролью POSTER; хранит `answer, updatedAt, decimals`. Инстансы: **ReserveAttestor** (граммы, decimals 0), **XauUsdFeed** (decimals 8, релей из Chainlink XAU/USD Ethereum mainnet), **UzsUsdFeed** (decimals 8, курс ЦБ) |
| **Exchange** | MINTER у OLTIN. Buy: UZD→OLTIN по фидам; Sell: OLTIN→UZD из трежери. Слиппедж-гард (minOut/maxIn). Staleness-гард на ОБА ценовых фида (Дизайн-Б) |
| **UZD** (есть) | Код без изменений; MINTER/BURNER — на ключ Bank-ops (Дизайн-А) |
| **OltinPaymaster** (есть) | Газлесс юзерских tx; монитор+top-up (прецедент `fund:rewards`) |

### 3.2 API — 7 bank / 6 user / 4 public (детализация в §5 плана; money двигают только банк-рельсы)
### 3.3 Console — Next.js, Bank Panel (auth) + PoR Dashboard (public); **дашборд читает ТОЛЬКО V3** (§7-Q5)
### 3.4 Money-path — webapp подписывает локально (viem, есть) → paymaster → цепь; API = индексер+банк-рельсы

## 4. ДИЗАЙН-А — Nonce & Key Strategy (БЛОКЕР #1, обязательный раздел)

**Проблема (VERIFIED):** `admin_tx.py:90` берёт `eth_getTransactionCount(addr,"pending")` per-call
без сериализации. PR-2 добавит к одному ключу: mint/burn UZD (депозиты/выводы) + 3 keeper-постера
→ конкурентные tx с одного адреса → гонка nonce («nonce too low»/replacement/дубль/потеря минта).
Это money-path.

**Решение:**
1. **Разнос ключей по ролям** (каждый — свой EOA, свой независимый nonce-поток):
   - `KEY_BANK_OPS` — UZD mint/burn (депозиты/выводы). BURNER/MINTER у UZD.
   - `KEY_RESERVE` — POSTER у ReserveAttestor.
   - `KEY_XAU` — POSTER у XauUsdFeed.
   - `KEY_UZS` — POSTER у UzsUsdFeed.
   - `KEY_DEPLOYER` — деплой/админ (offline после сетапа, не в рантайме).
   - Exchange минтит OLTIN сам (контракт), серверного ключа не требует.
2. **Сериализованный signer на КАЖДЫЙ ключ:** обёртка с `asyncio.Lock` на ключ + локальный
   счётчик nonce (init из `getTransactionCount(addr,"latest")` при старте; инкремент после
   успешного `sendRawTransaction`; ресинк из "latest" при `nonce too low`/рестарте). Ни один
   ключ не используется конкурентно by construction. Реализация — рефактор `admin_tx.py` в
   `SignerPool`/`NonceManagedSigner`, `send_admin_mint` становится методом.
3. **Идемпотентность выше подписи:** банк-эндпоинты идемпотентны по `bankTxId`/`auditRef`
   (уникальный индекс в БД + проверка ДО подписи) → ретрай не порождает второй минт даже при
   таймауте броадкаста.
4. **Инвариант:** конкурентная гонка nonce исключена (по одному in-flight tx на ключ);
   восстановление после сбоя — по идемпотентности + ресинк nonce.

**Тесты (§7):** конкурентные mint через один KEY_BANK_OPS → все проходят, nonce строго
монотонен, дублей нет; повтор с тем же `bankTxId` → второго on-chain минта НЕТ; ресинк после
смоделированного «nonce too low».

**Residual'ы к добитию ДО кода PR-2 (ревью-раунд 2, не блокируют PR-1):**
- **A1 (multi-worker):** `asyncio.Lock`+in-memory nonce процесс-локальны → при >1 uvicorn-воркере
  на ключ nonce-коллизия (идемпотентность спасает от двойного минта, но не от упавшей tx).
  Резолюция: либо **single-worker-на-ключ как задокументированный деплой-инвариант**, либо
  вынести lock+nonce в Redis (уже в стеке, `config.py:28`). Для демо single-worker ок — написать явно.
- **A2 (TOCTOU):** идемпотентность = **reserve-then-broadcast (insert-first)**, не check-then-act
  (иначе два конкурентных запроса оба «не нашли» → оба минтят). Шаблон уже есть —
  `welcome/service.py:53-67` (insert → IntegrityError → не минтим); переиспользовать.

## 5. ДИЗАЙН-Б — Oracle Guard: PoR + Staleness + Rounding (БЛОКЕР #2 + #4 + #5, обязательный)

**Гард минта (OltinTokenV3, сердце):**
```solidity
(, int256 r,, uint256 upd,) = reserveFeed.latestRoundData();
require(r > 0, "reserve<=0");
require(upd <= block.timestamp && block.timestamp - upd <= maxAgeReserve, "reserve stale"); // #4b
require(totalSupply() + amount <= uint256(r) * 10 ** (18 - reserveDecimals), "exceeds reserve");
```
- **decimals≤18 (finding #4a):** конструктор V3 валидирует `reserveFeed.decimals() <= 18`,
  кеширует `reserveDecimals` immutable → `10**(18-decimals)` без underflow.
- **upd>block.timestamp (finding #4b):** явная проверка `upd <= block.timestamp` → именованный
  revert (а не underflow-брик).

**Staleness на ОБА ценовых фида в Exchange (БЛОКЕР #2 + F16, ратифицировано merge PR #5):** buy/sell
читают XauUsd И UzsUsd; на каждый — `require(answer>0 && upd<=block.timestamp &&
block.timestamp-upd<=maxAge, "price stale")` с **ПЕР-ФИДОВЫМ окном**: XAU против `maxAgeXau`, UZS против
`maxAgeUzs` (F16: одно короткое окно роняло бы buy/sell по выходным ЦБ). Именованный revert; протух релей
→ сделка стоит.

**Fixed-point, protocol-safe округление — ПОЛНОСТЬЮ ЗАПИНЕНО (finding #5 / Q3 / преф-3):**
Константы: `GRAMS_PER_OZ_1E8 = 3110347680` (31.1034768×1e8). Фиды 8 decimals: `XAU_ANS` = USD/тр.унция ×1e8;
`UZS_ANS` = USD/UZS ×1e8. OLTIN и UZD = 18 decimals. Вся арифметика — OZ `Math.mulDiv(..., Rounding.Floor)`
(512-битный интермедиат, без overflow; ultracode математику НЕ импровизирует — только эти формулы):

- **Buy** `buy(uzdInWei, minOltinOut)`:
  `oltinOutWei = Math.mulDiv(uzdInWei * UZS_ANS, GRAMS_PER_OZ_1E8, 1e8 * XAU_ANS)` (floor);
  затем `require(oltinOutWei >= minOltinOut && minOltinOut > 0)` (dust→revert, fold-in #3).
  Порядок: pull `UZD.transferFrom(user → treasury, uzdInWei)` → `OLTIN.mint(user, oltinOutWei)`.
- **Sell** `sell(oltinInWei, minUzdOut)`:
  `uzdOutWei = Math.mulDiv(oltinInWei * XAU_ANS, 1e8, GRAMS_PER_OZ_1E8 * UZS_ANS)` (floor);
  `require(uzdOutWei >= minUzdOut)`; трежери < uzdOutWei → именованный revert ДО любых изменений.
  Порядок: `OLTIN.burnFrom(user, oltinInWei)` → `UZD.transfer(user, uzdOutWei)` из трежери.
- Обе — округление **вниз** = protocol-safe (buy: юзер не получит лишний OLTIN; sell: протокол не переплатит).
  Вывод формул (проверка размерности) зафиксирован; коэффициенты не менять.

**Reentrancy (преф-2):** buy/sell — OZ `ReentrancyGuard nonReentrant` + строгий checks-effects-interactions
(внешние вызовы UZD-трансфера / mint / burn — после всех проверок и вычислений).

**maxAge как immutable (преф-4 + F16):** `maxAgeReserve` (OltinTokenV3), `maxAgeXau` и `maxAgeUzs`
(Exchange) — конструкторные `immutable`, НЕ хардкод. Демо-значения (в main): reserve 3600 c, XAU 3600 c,
**UZS 259200 c (3 дня — переживает выходные ЦБ)**; финальные задаются аргументом деплоя.

**Sell жжёт OLTIN — non-custodial (fold-in #1 + преф-1, обязателен):** `Exchange.sell` жжёт ТОЛЬКО
средства юзера через allowance — `OLTIN.burnFrom(user, oltinIn)` (юзер заранее заапрувил) →
`totalSupply` СНИЖАЕТСЯ. **Ни роли, ни функции, жгущей у произвольного холдера** — иначе вернём
custodial-антипаттерн удалённого `adminTransfer` (уточнение finding #1 Ревьюера). **Attestor
самоштампует `updatedAt=block.timestamp`** в `postAnswer` (fold-in #2) — POSTER время не задаёт.

**Тесты (§7):** mint под потолком ок / +1 wei сверх → revert "exceeds reserve"; reserveFeed stale →
revert; r≤0 → revert; upd>now → revert; decimals=19 в конструкторе → revert; XAU stale / UZS
stale → buy revert; граничные округления (никогда не в пользу юзера); **sell снижает totalSupply
(fold-in #1); dust-buy (округление в 0 OLTIN) → revert по minOut>0 (fold-in #3)** — протокол не
забирает UZD молча за ноль токенов; **sell чужого баланса/без allowance → revert (non-custodial,
преф-1); reentrancy-атака на buy/sell → revert (преф-2)**.

## 6. Затронутые файлы (PR-1, детально; PR-2..5 — на своих кругах)

- **NEW** `contracts/contracts/OltinTokenV3.sol`, `Attestor.sol`, `Exchange.sol`
- **NEW** `contracts/scripts/deployV3.ts`, `keeper-xau.ts`, `keeper-uzs.ts`, `deploySecondAsset.ts` (пруф «gold is example»)
- **NEW** `contracts/test/OltinTokenV3.test.ts`, `Attestor.test.ts`, `Exchange.test.ts` (+ мутации)
- **NEW** `contracts/deployments-zk/zkSyncSepolia/*` (адреса V3)
- `contracts/hardhat.config.ts` (сети уже настроены — проверено; правок минимум)

## 7. Этапность PR (каждый — свой круг гейтов; порядок среза — §9 плана)

| PR | Содержимое | Ключевые критерии приёмки |
|---|---|---|
| **PR-1** (контракты) | V3 + Attestor×3 + Exchange, деплой Sepolia, keeper-скрипты, полное тест-покрытие + мутации | Все тесты §5 зелёные; **красные мутации доказаны** (diff мутанта + красный вывод); контракты verified на explorer; `adminTransfer` ОТСУТСТВУЕТ в ABI V3; **Exchange=BURNER и sell↓totalSupply (#1); Attestor self-stamp updatedAt (#2); dust-buy→revert (#3)** |
| **PR-2** (API) | Bank Connector (7) + user (6) + public (4); `SignerPool` (Дизайн-А); индексер-поллер; выпил DB-ledger | Идемпотентность bankTxId/auditRef; nonce-тесты §4; por-эндпоинты; money-path в цепи |
| **PR-3** (Console) | Bank Panel + PoR Dashboard (читает только V3) | Демо-сценарий проходит вживую |
| **PR-4** (webapp on-chain) | quote/buy/sell/transfer через paymaster; балансы из цепи; escrow по решающему правилу §8 | E2E-цикл зелёный |
| **PR-5** (docs) | README EN+RU, second-asset пруф, custody-модель по токенам (#8), формулировки (#9) | Греп-инвариант: 0 овер-клеймов |

**Ранняя чистка лендинга (§10-Q6, sequencing-правка Ревьюера):** удаление хайп-клеймов
(BlackRock/UBS/PoR-как-факт) — НЕ ждёт PR-5 (самый срезаемый). Отдельным быстрым коммитом в
начале (перед/вместе с PR-1), пока репо публичен во время судейства.

## 8. Решённые вопросы §10 (по ответам Ревьюера)

1. **Трежери на продаже:** отказ с подсказкой; демо-скрипт **предзаливает трежери**, чтобы отказ
   был показанным edge-case, а не залипанием на сцене. Авто-буфер-минт отклонён (rule #5).
2. **Escrow вывода — решающее правило (не выбор сейчас):** on-chain escrow в Exchange — **только
   если PR-4 остаётся в скоупе**; при срезе до PR-1+2+3 — burn-after-confirm с pending в БД (бёрн
   всё равно on-chain). Привязано к fallback-линии §9 плана.
3. **Fixed-point:** protocol-safe округление — см. Дизайн-Б.
4. **Welcome→demo-faucet:** оставить, за Bank Panel, явно «DEMO faucet». Переиспользует on-chain минт.
5. **V2 legacy:** V3 с нуля; V2 в legacy-секции README; **PoR-дашборд читает только V3** (orphan-supply
   V2 не пачкает coverage) — зафиксировано в §3.3.
6. **Хайп-чистка:** рано, отдельным коммитом (см. §7).

## 9. Тест-план (скелет; полнота — в PR)

Контракты (§5) + мутации m1..m3 (убрать staleness / убрать резерв-проверку / mint мимо Exchange →
каждая красит тест). API: идемпотентность, nonce-гонка (Дизайн-А), двухфазный вывод, por против
стаба. E2E testnet: аттестация 100 г → депозит → buy 5 OLTIN → transfer → sell → withdraw;
снижение аттестации до 3 г → buy блок, дашборд красный, sell работает. CI: 4 workflow зелёные.

## 10. Ops Капитану (не код)

**Верифицировать регуляторные факты ПЕРЕД публикацией в материалы жюри** (Ревьюер: из репо не
проверяются, неверный рег-клейм = удар по доверию): песочница НАПП/ЦБ с 01.01.2026, легальность
токенизир. ЦБ, прецедент AUZ — по citable-источнику (napp.uz/офиц.). Также: переподтвердить
дедлайн Incubation на awards.gov.uz.

## 11. Код-гейты (напоминание Ревьюера — обязательны, не опциональны)

PR-1/PR-2 = crypto + серверные ключи + mint/burn = граница доверия → **перед «коммитим?»:
/security-review обязателен** + ручной адверсариал по гарду (Дизайн-Б) + /testing на красные
мутации. Solidity-аналог /rust-review = ручной разбор гарда/ролей/reentrancy (Exchange sell,
escrow если on-chain).

## Definition of Done (эпик)
Все PR Стадий смержены (или срезаны по §9 с явной пометкой) · контракты V3 verified на Sepolia ·
инвариант supply≤резерв доказан тестом+мутацией · money-path в цепи · Console показывает живой PoR ·
README честный (custody-модель по токенам, «commodity/reserve-backed», без овер-клейма) · лендинг
вычищен · демо-сценарий воспроизводим · регуляторные факты подтверждены Капитаном.
