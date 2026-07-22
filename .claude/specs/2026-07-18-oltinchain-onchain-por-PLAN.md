# ПЛАН: OltinChain → полностью on-chain токенизация ценностей (PoR-рельсы для банков)

> Статус: **ПЛАН на ревью.** Порядок, заданный Капитаном: план → ревью Ревьюером (аппрув/дополнения)
> → спека Гейта-1 → «го» → код. Кода нет и не будет до спеки и «го».
> Кресло: Инженер. Репо: `temrjan/OltinPay`, рабочая копия `~/Dev/projects/oltinpay`, HEAD `c371651`.
> Контекст цели: President Tech Award, трек **FinTech Incubation** (дедлайн ≈10 авг — Капитану
> переподтвердить на awards.gov.uz); материалы UZ/RU/EN. Главная цель Капитана — **showcase
> компетенции** (глубина/ширина кода), выигрыш вторичен. ИИ в этот проект НЕ вшиваем (решение
> Капитана после анализа «GPT-обёртка = дисквалифицирующий признак»); это финтех-заявка.
> Все факты §2 проверены пробами этой сессии (file:line / on-chain вызовы); референсы §3 — с URL.

## 1. Цель — что мы показываем

Демонстрация **механизма токенизации обеспеченной ценности** на примере золота, так, чтобы
представитель банка за 5 минут понял «как я применю это у себя», а регулятор (НАПП/ЦБ) увидел
доказуемость обеспечения. Ядро — один инвариант, живущий on-chain:

```
totalSupply(OLTIN) ≤ аттестованный_резерв(граммы)   — всегда, проверяется контрактом при mint
```

Три роли → три поверхности:

| Роль | Поверхность | Что видит |
|---|---|---|
| **Банк/кастодиан** | Console: Bank Panel (новое) | Аттестация резерва («в хранилище N г») → on-chain потолок эмиссии; фиат-рельсы: подтверждение депозитов (mint UZD) и выводов (burn UZD); очередь выводов; свои обязательства |
| **Пользователь** | Telegram Mini App (есть, дорабатываем) | Ввод UZS→UZD, покупка/продажа OLTIN по оракульной цене, переводы; **каждая операция = реальная tx на zkSync Sepolia** со ссылкой на explorer |
| **Регулятор/публика** | Console: PoR Dashboard (новое, без auth) | Резерв vs эмиссия в реальном времени, coverage ratio, свежесть аттестации, история, цена XAU, ссылки на контракты. Красное состояние при coverage<1. Гвоздь демо: банк снижает аттестацию → минт встаёт на глазах |

Кошелёк — юзер-сторона; **токенизация и регулирование видны именно в Console** (требование
Капитана). Bank Panel = референс-имплементация банковской интеграции: в демо роль банка играет
оператор панели, реальный банк подключается теми же 7 эндпоинтами.

## 2. Текущее состояние (проверено пробами)

- **Контракты живут на zkSync Sepolia (chainId 300, RPC жив):** OLTIN V2
  `0x4A56B78DBFc2E6c914f5413B580e86ee1A474347` (код на месте, totalSupply ≈ 3 279.6e18),
  UZD `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32` (задеплоен, supply 0), staking
  `0x63e537…8314` (в config.py:52). Проверено eth_getCode/eth_call этой сессией.
- **Деньги в приложении ходят по Postgres, НЕ по цепи:** `oltinpay-api/src/transfers/service.py`
  — get_balance/deduct/add в БД; `OLTIN_PRICE_USD = Decimal("100")  # Fixed demo price`
  (service.py:27). API цепь не трогает (в config только адреса+RPC, приватного ключа нет).
- **Webapp уже non-custodial:** `src/lib/wallet.ts` — BIP39 (12 слов) + scrypt + AES-256-GCM,
  сид в Telegram Cloud Storage, viem HDAccount, путь `m/44'/60'/0'/0/0`. Подпись на клиенте есть
  — но сейчас не используется для денег (см. пред. пункт).
- **Дыры контракта V2 под нашу задачу:** `mint()` без какой-либо проверки обеспечения
  (OltinTokenV2.sol:46-55); `adminTransfer` — MINTER двигает средства юзера (строки 80-104),
  противоречит non-custodial истории.
- **Тесты контрактов:** только UZD / OltinToken(v1) / OltinStaking. **V2 и Paymaster без тестов.**
- **CI есть:** 4 workflow (api/contracts/webapp/deploy).
- **API-поверхность (существующая):** auth/telegram; users/{me,oltin-id,search,wallet};
  balances GET; transfers POST/GET/{id}; welcome/{status,claim}; staking GET; contacts;
  aylin/chat; health.
- **Chainlink:** Price Feeds live на zkSync Era **mainnet**; XAU/USD подтверждён на Ethereum
  mainnet; **на zkSync Sepolia XAU/USD НЕ подтверждён**; Functions на тестнете не подтверждён.
- **Регуляторный контекст:** песочница НАПП+ЦБ для стейблкоинов с 01.01.2026 (полное
  обеспечение, счёт в ЦБ); токенизированные акции/облигации разрешены с 01.01.2026; прецедент
  токенизированного золота под НАПП существует (AUZ, white paper на napp.uz). В UZD.sol:13 уже
  честный коммент «Production requires fiat reserve and НАПП stablecoin licence».

## 3. Референсы — лучшие решения и что берём

- **CACHE Gold (CGT) + Chainlink PoR «Secure Mint»** — наша модель 1-в-1: 1 токен = 1 грамм;
  PoR-фид как **circuit breaker в mint**: «off-chain резерв < supply после минта → минт
  останавливается». Берём механизм целиком.
  [chain.link/case-studies/cache-gold](https://chain.link/case-studies/cache-gold),
  [blog.chain.link/secure-mint](https://blog.chain.link/secure-mint/)
- **PAXG (Paxos)** — 1 токен = 1 тройская унция LBMA-бара; единый supplyController mint/burn;
  **transfer-fee для покрытия хранения** (парадигма нашего `transferFeeBps` — оставляем);
  **Allocation Lookup** (адрес → серийники баров) — берём идею для PoR-дашборда как
  «прозрачность выше традиционных продуктов»; редимшн от 430 oz (целый бар).
  [github.com/paxosglobal/paxos-gold-contract](https://github.com/paxosglobal/paxos-gold-contract),
  [paxos.com/pax-gold](https://www.paxos.com/pax-gold)
- **Tether Gold (XAUT)** — 1 токен = 1 oz, allocated в Швейцарии, свой lookup. Упоминаем как
  рынок, паттернов сверх PAXG не добавляет.
- **Вывод для нарратива:** «инфинит-минт без обеспечения» — главный страх регулятора; Secure
  Mint — отраслевой ответ; мы показываем его на zkSync + локальные рельсы (UZD, банк-коннектор).

## 4. Целевая архитектура

### 4.1 Контракты (Solidity, hardhat-zksync; деплой zkSync Sepolia)

| Контракт | Статус | Суть |
|---|---|---|
| `OltinTokenV3` | новый (редеплой) | ERC20 «1 OLTIN = 1 г золота». **Mint гейтится PoR-фидом** (гард ниже). `adminTransfer` УДАЛЁН. Роли: MINTER (только Exchange), BURNER, PAUSER. transferFeeBps остаётся |
| `Attestor` | новый, 1 код × 3 инстанса | AggregatorV3Interface-совместимый пост значений с ролью POSTER + `maxAge`. Инстансы: **ReserveAttestor** (граммы в хранилище; постит Bank Connector), **XauUsdFeed** (релей цены из Chainlink XAU/USD Ethereum mainnet керер-скриптом), **UzsUsdFeed** (официальный курс ЦБ, раз в день) |
| `Exchange` | новый | Покупка: юзер платит UZD → Exchange минтит OLTIN по цене фидов; продажа: OLTIN → UZD из трежери. Слиппедж-гард (minOut/maxIn). Цена: `грамм_USD = XAU_USD / 31.1034768`, далее × UZS/USD |
| `UZD` | есть | Без изменений кода; MINTER/BURNER переезжают на ключ Bank Connector |
| `OltinPaymaster` | есть | Газлесс для юзерских tx; монитор баланса + top-up скрипт (прецедент `fund:rewards`) |

**Гард минта (сердце плана, версия после /check):**
```solidity
(, int256 r,, uint256 upd,) = reserveFeed.latestRoundData();
require(r > 0, "bad reserve");
require(block.timestamp - upd <= maxAge, "stale attestation");   // протухла — минт стоит
require(totalSupply() + amount <= uint256(r) * 10 ** (18 - reserveFeed.decimals()),
        "exceeds proven reserve");
```
Политика coverage<1 (банк снизил аттестацию ниже supply): **минт стоит, редимшн/бёрн работает**
(паттерн Paxos/Secure Mint), дашборд в красном.

**Интерфейс = Chainlink:** на mainnet-деплое Attestor-инстансы свопаются на нативные Chainlink
PoR/Data Feeds конструкторным аргументом, без правки токена. Это честная формула «Chainlink-
совместимая PoR-архитектура; цена релеится из Chainlink XAU/USD» — без овер-клейма про фиды,
которых на Sepolia нет.

### 4.2 API (FastAPI; существующие неймспейсы сохраняются)

Деньги двигают ТОЛЬКО банк-рельсы; юзерские покупки/продажи/переводы — клиентская подпись
прямо в цепь (paymaster), API их не проводит, а индексирует.

| Группа | Эндпоинты (метод путь) | Назначение |
|---|---|---|
| **Bank `/api/v1/bank/*`** (API-key; в проде mTLS) — 7 | `POST /attestations` (граммы, auditRef; идемпотентно по auditRef) · `GET /attestations/latest` · `POST /fx` (курс ЦБ) · `POST /deposits` (bankTxId, идемпотентно → mint UZD) · `GET /withdrawals?status=pending` · `POST /withdrawals/{id}/confirm` (burn) · `POST /withdrawals/{id}/reject` (release) | Весь банковский контракт интеграции |
| **User** (Telegram initData) — 6 | `auth/telegram`, `users/*` (как есть) · `GET /balances` → **читает цепь** · `POST /deposits` (интент, демо-реквизиты) · `POST /withdrawals` (двухфазный: escrow→confirm/expiry-refund) · `GET /quote` (превью цены из фидов) · `GET /transactions` (индексер + explorer-links) | Mini App |
| **Public** — 4 | `GET /por` (резерв, supply, coverage, свежесть, адреса) · `GET /por/history` · `GET /rates` · `GET /health` | PoR Dashboard и любой желающий |

Судьба существующих: `transfers POST` (DB-ledger) — **hard-switch** на on-chain (реальных
юзеров 0 — проверено в разборе БД); `welcome/claim` → «demo faucet»: кнопка «симулировать
депозит» в Bank Panel (зрителю нужны средства, чтобы поиграть); `staking`, `aylin/chat`,
`contacts` — не трогаем (вне скоупа).

### 4.3 Console (новое приложение: Next.js, один app, две вью)

- **Bank Panel** (auth): форма аттестации (граммы + auditRef → tx), подтверждение
  депозитов/выводов, сводка обязательств (UZD supply, OLTIN vs резерв), кнопка demo-faucet.
- **PoR Dashboard** (public): инвариант живьём — резерв vs эмиссия, coverage, возраст
  аттестации, цена XAU/грамм в UZS, история аттестаций (события), ссылки на контракты/txs.
  Идея PAXG-lookup: «покажи обеспечение моего адреса».

### 4.4 Money-path (миграция)

Было: Postgres-ledger. Станет: webapp подписывает tx локально (viem, уже умеет) → paymaster
платит газ → цепь; API-индексер слушает события (Minted/Burned/AdminTransfer→нет/Transfer/
Attested) → `GET /transactions`, `GET /por/history`. Фиатная нога честно off-chain (банк), её
on-chain след — mint/burn UZD с bankTxId в событии.

## 5. README и позиционирование

Структура (EN основной + RU зеркало `README.ru.md`; UZ — в конкурсных материалах):
1. Тезис: *«Proof-of-reserve tokenization rails for real-world value — gold first»*.
2. Инвариант + диаграмма трёх ролей.
3. Live demo: адреса (V3 + история V2), explorer, Mini App, PoR Dashboard.
4. Архитектура + таблица эндпоинтов (банковский контракт интеграции — витрина для банков).
5. **«Gold is the example, not the limit»**: тот же контракт с другими конструкторными
   аргументами = любая обеспеченная ценность (хлопок, зерно, ЦБ по закону с 01.2026,
   недвижимость). Пруф: деплой-скрипт второго актива одной командой (без multi-asset factory —
   решение /check §7).
6. Chainlink: что live сейчас (Secure-Mint-паттерн, релей цены), что свопается в проде (PoR,
   нативные фиды).
7. **Deployment models / suverenitet:** публичный zkSync Era → **sovereign ZK Stack chain**
   (национальный/консорциумный чейн, контракты без изменений) → permissioned EVM (Besu).
   Формулировка «свой блокчейн» — только так, слово «форк» не используем (техточность).
8. Honesty box: DEMO на testnet, токены без стоимости; прод требует кастодиана, аудита,
   лицензии НАПП; цель — песочница НАПП/ЦБ. (Хайп-клеймы BlackRock/UBS/PoR-как-факт с лендинга
   убираем — конфликт с фактчеком жюри.)
9. Quickstart + тесты + демо-сценарий.

## 6. Этапность (каждый PR — свой круг гейтов)

| PR | Содержимое | Зависимости |
|---|---|---|
| **PR-1** | Контракты: V3 + Attestor + Exchange; полное тест-покрытие (вкл. красные мутации); деплой Sepolia; керер-скрипты (XAU-релей, курс ЦБ) | — |
| **PR-2** | Bank Connector API + индексер + public PoR эндпоинты; идемпотентность; выпил DB-ledger | PR-1 |
| **PR-3** | Console (Bank Panel + PoR Dashboard) | PR-2 |
| **PR-4** | Webapp money-path on-chain (quote/buy/sell/transfer через paymaster; балансы из цепи) | PR-1 (частично ∥ PR-2/3) |
| **PR-5** | README/docs (EN+RU), демо-сценарий, second-asset деплой-пруф, чистка лендинга от хайпа | все |

## 7. Тест-план (скелет; развернётся в спеке)

- **Контракты (hardhat):** V3 — mint под потолком ок / сверх → revert "exceeds proven reserve" /
  stale-фид → revert / отрицательный answer → revert / decimals-скейлинг / pause / отсутствие
  adminTransfer в ABI. Attestor — только POSTER, maxAge, события. Exchange — цена из двух фидов
  (формула грамм), слиппедж, продажа при пустом трежери → именованный отказ.
  **Красные мутации:** (m1) убрать staleness-гард → тест красный; (m2) убрать проверку резерва →
  красный; (m3) mint мимо Exchange → красный.
- **API (pytest):** идемпотентность bankTxId/auditRef (повтор → 200, второго минта нет);
  двухфазный вывод (confirm/reject/expiry); por-эндпоинты против стаба цепи.
- **E2E (testnet):** полный цикл: аттестация 100 г → депозит → покупка 5 OLTIN → перевод →
  продажа → вывод; снижение аттестации до 3 г → покупка блокируется, дашборд красный, продажа
  работает. Всё с tx-ссылками.
- **Гейты CI:** существующие 4 workflow зелёные.

## 8. Не входит (скоуп-граница)

Реальное золото/кастодиан/лицензия (прод-фаза, песочница); mainnet-деплой; изменения
staking/aylin/contacts; multi-asset factory; мобильный native; ИИ-функции; смена лендинг-стека
(только чистка текстов от овер-клейма).

## 9. Риски и фолбэки

- **Testnet/RPC упал на живом питче** → локальный anvil-zksync форк + записанный прогон.
- **Paymaster без газа** → монитор + top-up скрипт (PR-2).
- **Faucet-лимиты Sepolia ETH** → пополнить заранее, держать резерв на деплой-ключе.
- **Chainlink XAU-релей: mainnet RPC-лимиты** → публичные RPC ×2 + кеш последнего значения
  (свежесть контролирует maxAge on-chain).
- **Срок ≈3 недели соло+AI** → этапность §6 позволяет резать с хвоста: минимальный убедительный
  набор = PR-1+PR-2+PR-3 (механизм+банк-контракт+витрина); PR-4 (webapp on-chain) — вторая
  очередь, PR-5 сжимаем.

## 10. Открытые вопросы Ревьюеру

1. **Exchange-трежери на продаже:** пустой → отказ с подсказкой «банк пополняет» — достаточно
   для демо, или нужен авто-механизм (буферный минт UZD под залог резерва)? Моя рекомендация:
   отказ, механика честнее.
2. **Escrow вывода:** on-chain escrow в Exchange vs burn-after-confirm с pending в БД. Моя
   рекомендация: on-chain escrow (сильнее история «всё on-chain»), цена — +1 функция контракта.
3. **Формула цены:** конверсия oz→грамм константой 31.1034768 в Exchange (fixed-point 1e8) —
   проверить точность/округления.
4. **Welcome bonus как demo-faucet** через Bank Panel — ок, или убрать вовсе?
5. **V2-токен с supply 3 279:** оставить как исторический (README-таблица «V2 legacy») — или
   burn-визуально мешает PoR-дашборду? Моя рекомендация: V3 с нуля, V2 в legacy-секции.
6. **Хайп-чистка лендинга** (BlackRock/UBS/PoR-клеймы) — подтвердить, что входит в PR-5 и не
   требует отдельного решения Капитана.

## Демо-сценарий (5 минут, для банка/жюри)

1. PoR Dashboard: резерв 0, supply 0. 2. Bank Panel: аттестация «100 г, audit#1» → tx →
дашборд: потолок 100. 3. Faucet-депозит юзеру → UZD mint tx. 4. Mini App: покупка 5 OLTIN по
живой цене (XAU×UZS) → tx, дашборд: 5/100. 5. Перевод другу → tx. 6. **Гвоздь:** банк снижает
аттестацию до 3 г → покупка в Mini App блокируется («exceeds proven reserve»), дашборд красный,
продажа работает. 7. Продажа+вывод → burn. 8. README: «то же — для хлопка/ЦБ/недвижимости;
тот же код — на sovereign ZK Stack chain».
