# PR-4 — webapp money-path полностью on-chain — Гейт-1 ПЛАН

На ревью Ревьюеру (план, не спека; код не начат). База — актуальный main
(`d0edeb8` + PR-3 Console в ветке). Цель: юзерский money-path (buy/sell/transfer/
withdraw) — реальные client-signed tx, gasless через paymaster; балансы из цепи;
DB-ledger выпилен; закрыт весь отложенный-в-PR-4 бакет. Итог разблокирует
постоянный cutover `api.oltinpay.com` → новый API (webapp станет совместим).

## §2 Текущее состояние — верифицировано пробами (file:line)

### Webapp (money-path сейчас = мёртвые/DB эндпоинты, но signing-инфра ГОТОВА)
- `src/lib/api.ts:127-209` — exchange-методы зовут `/exchange/price|orderbook|
  orders|trades` + swap; `api.ts:85` — `/balances/transfer`; `api.ts:108-116` —
  `/staking/deposit|withdraw`. **Этих эндпоинтов НЕТ в API** — `src/main.py:12-27`
  (список роутеров: auth/aylin/balances/bank/contacts/deposits/transactions/por/
  staking/transfers/users/welcome/withdrawals — exchange-роутера нет). Это же
  зафиксировано в `webapp/eslint.config.mjs` (коммент: «api.ts still calls
  removed endpoints (/exchange, /staking/deposit, /balances/transfer)»).
- `src/app/exchange/page.tsx:21-47` — `api.getPrice()/getSwapQuote()/
  executeSwap()` (мёртвые). `src/app/send/page.tsx:75-77` —
  `api.createTransfer()` → `POST /transfers` (жив, но DB-ledger — ниже).
  `src/app/wallet/page.tsx:32-61` — `api.getBalances()` + ожидает СТАРУЮ форму
  (`balancesData[account]`, `total_usd`) — новый `BalancesResponse` (wallet/
  staking wei) её не отдаёт → wallet-страница уже частично несовместима.
- **Signing-инфра есть:** `src/lib/wallet.ts:17-51` (BIP39 → viem `HDAccount`,
  HD-путь, PIN-шифрование мнемоники); `src/lib/chain.ts:9-27` (viem
  `zksyncSepoliaTestnet`, publicClient + `makeWalletClient(account)`);
  `src/lib/contracts.ts:16+` (ERC20_ABI с `transfer`, STAKING_ABI).
- 🔴 `src/lib/contracts.ts:9-13` — **адрес OLTIN СТАРЫЙ**
  (`0x4A56B78…4347`, до-V3; V3 = `0x906bcf…5B3A5` по `docs/DEPLOYMENTS.md`),
  UZD совпадает, STAKING старый. PR-4c обязан перевести на V3-стек.

### API (split-brain УЖЕ ЖИВОЙ в main)
- `src/balances/service.py:1-7` — «The backend does not store balances anymore.
  All reads go through RPC» → `GET /balances` **уже chain-read** (balanceOf
  OLTIN/UZD + staking, gather).
- НО `src/transfers/service.py` — **DB-ledger**: `:26` `OLTIN_PRICE_USD =
  Decimal("100")  # Fixed demo price`; `:78-93` читает/мутирует `Balance`-строки.
  → **сплит сегодня**: `POST /transfers` двигает DB-строки, которые `GET
  /balances` НЕ читает — перевод «исчезает» для баланса. PR-2 Q5-риск не
  гипотеза, он в main.
- `src/balances/db.py:1-6` — «Legacy DB helpers … used by transfers/ and
  staking/ … retired when moved to on-chain»; `src/balances/models.py:38+` —
  таблица `balances` (+ CHECK amount≥0); `src/users/service.py:49-67` — при
  создании юзера сеются 5 Balance-строк. Всё это — целевой выпил.
- `src/users/router.py:68-89` — `POST /users/wallet`: first-call-wins, БЕЗ
  доказательства владения (M1-мишень). `src/main.py:21` — `/transactions`
  (индексер, PR-2) — готовый источник истории для webapp.

### Контракты
- `contracts/OltinPaymaster.sol` СУЩЕСТВУЕТ: `:22` IPaymaster+Ownable, `:82` —
  **только `approvalBased`-flow** (фи в токене; конструктор берёт OLTIN),
  `:142-157` owner-функции. `scripts/deployPaymaster.ts` есть. **НЕ задеплоен**:
  в `docs/DEPLOYMENTS.md` (V3-стек 2026-07-18) paymaster-адреса нет, деплой шёл
  только `deploy/deployV3.ts`.
- `contracts/Exchange.sol`: `:119` `buy(uzdInWei, minOltinOut)`, `:156`
  `sell(oltinInWei, minUzdOut)` — слиппедж-защита уже есть; **escrow-функций
  нет**; `:41` — «no rescue/migration function on this Exchange» (менять
  Exchange = редеплой + пере-грант MINTER + смена адресов везде).
- `OltinTokenV3` — стандартный ERC20 `transfer` покрывает user-переводы;
  UZD `burnFrom` allowance-gated (PR-1).

### CI
- `.github/workflows/webapp.yml` — только typecheck+lint, **тестов нет** (джоб
  «test» отсутствует). PR-4c обязан добавить (урок «тест есть — в CI не бежит»).

## §3 Бакет PR-4 — все 7 пунктов → где адресованы
| # | Пункт | Куда |
|---|---|---|
| 1 | Money-path flip (buy/sell через Exchange + transfer ERC20, client-signed, gasless) | PR-4c (+4a paymaster) |
| 2 | Балансы из цепи + выпил DB-ledger (transfers/service, `balances`-таблица, `OLTIN_PRICE_USD=100`) | PR-4b (балансы УЖЕ chain — остаётся выпил write-пути) |
| 3 | `/balances` chain-read | **уже сделан** (proof выше) — в PR-4b только снос legacy `db.py`/models |
| 4 | Escrow вывода (§8-правило PR-1) | PR-4a — развилка F1 |
| 5 | Реконсилятор (RECONCILE-выводы + phantom-депозиты по tx_hash) | PR-4b |
| 6 | M1 EIP-191 ownership-proof (`POST /users/wallet`) | PR-4b — развилка F4 |
| 7 | Постоянный cutover api.oltinpay.com | PR-4d — развилка F3 |

## §4 Суб-стадии (каждая — свой круг гейтов) + fallback-порядок

- **PR-4a — контракты**: `WithdrawalEscrow` (новый, отдельный — F1) +
  переработка `OltinPaymaster` (F2) + деплой обоих + wiring. Гейт-2 = флот +
  security (крипто-код). V3/Exchange НЕ трогаем (Дизайн-Б цел).
- **PR-4b — API**: реконсилятор (фоновая джоба: RECONCILE-выводы →
  status==1→CONFIRMED / dropped→освободить; phantom-mint-строки deposit/welcome/
  attestation → досеттлить) + M1 EIP-191 + выпил transfers-DB (роутер/сервис →
  замена на `/transactions`-историю), `balances/db.py`, `Balance`-модель,
  5 initial-строк в `users/service`, `OLTIN_PRICE_USD`) + escrow-aware confirm.
- **PR-4c — webapp**: `contracts.ts` → V3-адреса; exchange-страница → viem
  `approve(UZD)`+`Exchange.buy/sell` (+minOut из `/quote`); send → `ERC20.
  transfer`; withdraw → escrow.lock; wallet — новая схема балансов; история —
  `/transactions`; чистка мёртвых api.ts-методов; paymaster-параметры (zksync
  EIP-712, viem ^2.48 поддерживает); optimistic-UI + `waitForTransactionReceipt`;
  **CI: добавить test-джоб**.
- **PR-4d — ops cutover**: 7demo-свап по уже разведанному плану (git-pull
  `/opt/oltinpay`, env, `docker rm -f oltinpay-api` → новый compose up,
  Caddy не трогаем — alias тот же; откат = поднять старый), keeper+seed,
  Console-домен.

**Fallback-порядок под 10 авг** (режется с хвоста, минимальный убедительный
набор = 4c+4d + реконсилятор из 4b):
1. Первым режется **escrow** (F1: вклад в демо мал — выводы уже защищены cap'ом);
2. вторым — **paymaster** (fallback: gas-stipend — BANK_OPS шлёт новым кошелькам
   пыль ETH на 5-10 tx; UX чуть хуже, зато ноль контракт-рисков);
3. M1 (дёшев) и реконсилятор (корректность денег) — НЕ режутся.

## §5 Крукс-развилки — на ратификацию Гейта-1

**F1 Escrow: отдельный контракт (реком) vs модификация Exchange vs
burn-after-confirm.** Реком: **новый `WithdrawalEscrow`** (user client-signed
`approve`+`lock(amount)`; bank confirm → escrow `burnFrom`-настоящий burn;
reject → refund). *Почему:* §8-правило ратифицировано («PR-4 в скоупе →
on-chain»); отдельный контракт не трогает Exchange/V3 (`:41` no-rescue →
редеплой Exchange = каскад адресов). *Контр:* +контракт, +деплой, +флот-гейт —
самый дорогой кусок PR-4; burn-after-confirm без контракта, но оставляет
§8-окно (юзер уводит UZD между заявкой и confirm). *Цена ошибки:* контракт
изолирован, откат = не использовать. *Что изменит выбор:* дедлайн-прессинг →
fallback #1 (резать с явной ре-ратификацией §8-отсрочки).

**F2 Paymaster-политика.** Текущий контракт — только `approvalBased` с фи в
OLTIN → **catch-22**: свежий юзер (после депозита имеет только UZD) не может
оплатить фи первой покупки OLTIN. Реком: **переработать до general
(sponsored) flow** + allowlist целевых контрактов (OLTIN/UZD/Exchange/Escrow) +
per-sender дневной лимит; задеплоить, фандить ETH, монитор+top-up (прецедент
fund:rewards). *Контр:* sponsored = платим весь газ; на Sepolia это бесплатно
по сути, лимит держит абьюз. *Цена ошибки:* paymaster недеплоен/пуст → fallback
gas-stipend (см. §4). *Изменит выбор:* если approvalBased-в-UZD окажется
тривиальнее — решим в спеке PR-4a (исследование paymaster'а — ПЕРВЫЙ шаг 4a).

**F3 Cutover-стратегия.** Реком: **двухфазный свап**: (i) СЕЙЧАС (=E4, до
PR-4) свапнуть api.oltinpay.com на PR-2-API ради живого Console-демо — старый
webapp-money-path и так мёртв против нового API (см. §2: exchange-эндпоинтов
нет), а balances/welcome/auth/wallet работают; (ii) после PR-4c — webapp
полностью совместим, свап становится постоянным без деградации. *Контр:*
в окне (i)→(ii) app.oltinpay.com с деградированным exchange/send — партнёр
может увидеть. Митигация: мини-патч webapp «Coming soon» на сломанные экраны
(1 экран-баннер, вне PR-4-скоупа, chore). *Цена ошибки:* низкая (testnet),
откат — поднять старый контейнер (секунды). *Изменит выбор:* если Капитан
хочет ноль деградации webapp — свап только после PR-4c (Console-демо ждёт).

**F4 M1 EIP-191.** Реком: challenge = `personal_sign` строки
`OltinPay bind: {oltin_id}|{nonce}|{ts}|chain:300` (nonce+ts одноразовые,
сервер выдаёт и верифицирует recover==address). Существующие привязки —
grandfather (не ломаем юзеров), новые — только с подписью. *Контр:* grandfather
оставляет старые непруфнутые привязки; их мало (демо), cap прикрывает.

**F5 Атомарность флипа.** Реком: 4b (выпил DB-write) и 4c (client-signed
замена) — отдельные PR, но **cutover одним шагом** (4d): пока оба не в main,
прод-API остаётся старым. Между merge 4b и 4c webapp-send мёртв ТОЛЬКО на новом
API, который ещё не в проде → сплита у юзеров нет. *Контр:* длинная ветка-очередь;
митигация — суб-PR мержатся быстро друг за другом.

## §6 Пороговые риски → адресация
- **Split-brain** — уже в main (§2 proof); лечится ровно порядком F5.
- **Финальность client-tx**: webapp: optimistic UI → `waitForTransactionReceipt`
  → revert = откат UI + тост; история — `/transactions` (индексер уже пишет).
  B2-урок применён на клиенте.
- **Nonce client-signed**: per-account nonce ведёт viem от RPC; один юзер = одно
  устройство (low concurrency). Paymaster (EIP-712 type 0x71) НЕ меняет nonce
  аккаунта — проверка в исследовании 4a.
- **CI**: 4a — contracts-CI уже полный (PR #4); 4b — api-CI полный (PR #9);
  4c — **добавить webapp test-джоб** (сейчас нет вообще); красные мутации на
  каждый новый гейт (§7).
- **Демо не уронить**: Console бьёт в `/por|/rates|/bank/*` — PR-4b их не
  трогает (выпил только transfers/balances-legacy); прогон Console-смоука в
  отчёте 4b.

## §7 Тест-план (скелет, red-мутации на каждую ветку)
- 4a: escrow lock→confirm burn / reject refund / double-confirm revert (мутации:
  убрать guard → тест краснеет); paymaster: allowlisted ок / чужой контракт
  revert / лимит исчерпан revert.
- 4b: реконсилятор: RECONCILE+status1→CONFIRMED; RECONCILE+dropped→release;
  phantom-deposit→settle (мутация: реконсилятор помечает без проверки чейна →
  красный); M1: без подписи/чужая подпись → 4xx (мутация: снять verify);
  выпил: `pytest` весь — ни один живой эндпоинт не осиротел.
- 4c (vitest): buy-флоу собирает корректные calldata (approve+buy, minOut);
  transfer — верный ERC20 call; receipt-revert → UI-откат; форма балансов —
  новая схема (мутация: старое поле → красный).
- 4d: смоук-чеклист (curl /por, Console «гвоздь», webapp happy-path) в отчёте.

## §8 Не входит
Mainnet; реальный кастодиан/лицензия; multi-asset factory; native-mobile; ИИ;
staking-write-path редизайн (отдельно, если всплывёт); ре-дизайн Exchange.

## §9 Чтимое (не переоткрываем)
Non-custodial (adminTransfer нет, burn allowance-gated — client-signed усиливает);
A1 single-writer/ключ (серверные роли; client-tx подписывает юзер — вне A1);
A2 reserve-then-broadcast; B2 receipt==1 (сервер) → на клиенте зеркалим
waitForReceipt; индексер — простой поллер; Дизайн-Б гард V3 не трогаем;
без AI-подписей; testing red→green.

## §10 Открытые вопросы Ревьюеру
1. F1 — отдельный WithdrawalEscrow: ок? (И согласие, что escrow — первый
   кандидат на срез при дедлайне, с ре-ратификацией §8.)
2. F2 — general/sponsored paymaster c allowlist+лимитом vs approvalBased-UZD:
   предварительная позиция? (Финал — после исследования, первым шагом 4a.)
3. F3 — двухфазный cutover (свап сейчас ради Console-демо, деградация webapp до
   4c): приемлемо? [+ Капитану — ценностная часть]
4. F5 — очередь мержей 4a→4b→4c→4d с cutover'ом одним шагом: ок?
5. Grandfather старых wallet-привязок (F4): ок?

**Стоп-условие**: код не начат; деливерабл — этот план. После ратификации —
спека (по суб-стадиям), «го», код.
