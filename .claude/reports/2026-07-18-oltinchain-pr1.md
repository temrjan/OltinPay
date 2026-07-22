# Отчёт Гейта-2: PR-1 OltinChain (контракты PoR)

> Кресло: Инженер → Ревьюеру (через Капитана) на **обязательный адверсариал §11**.
> Ветка: `pr-1-oltin-v3` @ `acfd102` (git root `~/Dev/projects/oltinpay`). **НЕ запушено, PR не открыт**
> (жду «чисто»). main нетронут на `c371651`. Спека: `.claude/specs/2026-07-18-oltinchain-onchain-por-SPEC.md`.
> База: `pr-1-oltin-v3` = main + **1 коммит** (acfd102, 13 файлов, +1741). Без AI-подписи (проверено).

## ⚠️ Провенанс (читать первым — влияет на доверие к ревью)
Код PR-1 **сгенерирован ultracode-воркфлоу**, не рукописный. Таймлайн (по birth-таймстампам + reflog):
- 12:02 — свежий клон (чисто).
- **14:48–15:02 — ПЕРВЫЙ ultracode написал весь PR-1** (Implement-агент доработал после того, как оркестратор был остановлен).
- 15:15–15:36 — **ВТОРОЙ ultracode** верифицировал (101 тест), доказал мутации, провёл внутренний 3-линзовый ревью, закоммитил `acfd102`.

**Вывод для тебя:** внутренний ревью — это первый слой, НЕ замена твоего адверсариала. Относись к дифу как к AI-сгенерированному коду на границе доверия (crypto + mint/burn) — верифицируй независимо.

## Сделано (по §7 спеки) — с доказательствами
- **Контракты:** `OltinTokenV3.sol` (141), `Attestor.sol` (76, 1 код × 3 инстанса), `Exchange.sol` (185), `interfaces/AggregatorV3Interface.sol` (31), `mocks/{MockAttestor,MaliciousReentrant}.sol`.
- **Дизайн-Б гард — в коммите цел** (перепроверил после мутационного отката): конструктор `require(d <= 18, "reserve decimals>18")` + immutable `reserveDecimals`; mint `onlyRole(MINTER_ROLE)` + `"reserve stale"` + `totalSupply()+amount <= r*10**(18-reserveDecimals)` `"exceeds reserve"`.
- **Exchange:** `nonReentrant` + `Math.mulDiv` + `GRAMS_PER_OZ_1E8=3110347680` + allowance-gated `burnFrom(msg.sender)` + dual-feed staleness. Без `adminTransfer`, без BURNER-роли.
- **Тесты:** `npx hardhat test` → **101 passing, 0 failing** (Node 20). PR-1 = 52 (OltinTokenV3 25, Exchange 19, Attestor 8); 49 — прежние UZD/OltinToken/OltinStaking, зелёные.
- **Compile:** `npx hardhat compile --force` → «Successfully compiled 63 Solidity files», 0 warnings.
- **Красные мутации m1–m3 — все доказаны красными и откачены** (дерево чистое/зелёное):
  - m1 (снят staleness в mint) → красит `OltinTokenV3.test.ts:144 "reverts when reserve is stale"` (+`:179` future-dated). 2 failing.
  - m2 (снят резерв-кап) → красит `:125 "reverts one wei over cap"` (+`:135` cumulative, `:202` decimals-scaling). 3 failing.
  - m3 (снят `onlyRole(MINTER)`) → красит `:210 "reverts for a non-minter" (AccessControlUnauthorizedAccount)`. 1 failing.
- **Коммит:** 13 файлов адресно (не `-A`), artifacts-zk НЕ включены, без AI-подписи (сообщение проверено).

## Само-ревью (Инженер, до отчёта)
- Диф прочитан; scope = 13 файлов = спека; секретов/дебага нет (греп `0x{64}`/PRIVATE_KEY/mnemonic/api_key/BEGIN PRIVATE — чисто; `console.log` только в деплой-скриптах как operator-вывод).
- Внутренний 3-линзовый адверсариал: **4 находки, 0 блокеров** (все ниты, ниже).

## Внутренние ниты (0 блокеров) — на твою верификацию
1. **`Exchange.sell` без dust-гарда** (security): `buy` имеет `minOut>0`, `sell` — только `>=minUzdOut`, без `uzdOutWei>0`. Пыльная продажа жжёт OLTIN за 0 UZD (вредит только вызывающему; нарушает fold-in #3 на sell-стороне). Фикс: `require(uzdOutWei >= minUzdOut && uzdOutWei > 0)`.
2. **Exchange не валидирует `feed.decimals()==8`** у XAU/UZS (хардкод `1e8`); OltinTokenV3 свой резерв-фид валидирует. Defense-in-depth (фиды immutable). Фикс: `require(xauFeed.decimals()==8 && uzsFeed.decimals()==8)`.
3. **Zero-address ctor-тест** (`OltinTokenV3.test.ts:100`) проверяет `.to.be.reverted` — пройдёт даже если снять `"Zero address"` guard (высокоуровневый call к address(0) ревертит сам). Мутант выживает. Фикс: `.revertedWith("Zero address")`.
4. **`upd>now` в `Exchange._freshPrice` не покрыт тестом** (у резерва на уровне токена — покрыт). Мутант, снявший `upd<=block.timestamp` в `_freshPrice`, выживает. Фикс: buy-тест с future-dated MockAttestor.

## Не сделано / отложено (по дизайну — не Инженера)
- **Деплой V3 на zkSync Sepolia + verify + запись адресов** в `deployments-zk/` (нужен фондированный ключ — op Капитана; §7-критерий, держит DoD).
- **Gap-фиксы:** `package.json` (скрипты `deploy:v3`/`deploy:second`/`keeper:*` отсутствуют), `.env.example` (~15 новых env-vars), `.gitignore` (`artifacts-zk/`+`cache-zk/`).
- **CI:** `.github/workflows/contracts.yml` гоняет только UZD+OltinStaking — новые сьюты (52 кейса) НЕ в CI. Фикс существует на **отдельной ветке `chore/ci-hardening`** (первый воркфлоу), в PR-1 НЕ влит → см. Вопрос 4.
- 4 нита выше — не фикшены.

## Замечено, не трогаю (вне скоупа)
- Рабочее дерево: 37 `M` в `artifacts-zk/*.dbg.json` (от рекомпайла) — не закоммичены, коммитить нельзя; чистка (`gitignore`+`rm --cached`) — отдельный hygiene-коммит.
- `buy` возвращает `"dust"` и для пыли, и для непройденного `minOltinOut` (slippage) — функционально верно, но строка неточная, если грепать «slippage».

## Отклонения от плана и почему
1. **Имя ветки `pr-1-oltin-v3`**, а не `feature/pr1-onchain-por` (спека §7): при re-invoke воркфлоу args не долетели (`REPO/SPEC/BRANCH=undefined` в промптах), агенты легли на ветку, созданную первым воркфлоу. Безопасно (main цел), но имя другое — см. Вопрос 3.
2. **§7 говорит «Exchange=BURNER»**, реализовано **allowance-gated `burnFrom`** без BURNER-роли — это НАМЕРЕННО, по §5 + преф-1 (non-custodial; роль-жечь-чужое = запрещённый custodial-паттерн). Деплой даёт Exchange только MINTER.
3. **Exchange группирует множители `Math.mulDiv` иначе, чем буквальная формула** (`uzdInWei` как x; `uzsAns*GRAMS_PER_OZ_1E8` как y) — математически идентично (тот же числитель/знаменатель, Floor), сделано чтобы избежать overflow пред-умножения. Внутренний correctness-ревьюер подтвердил; **прошу тебя перепроверить эквивалентность независимо**.

## Вопросы Ревьюеру
1. **Обязательный §11:** прошу адверсариал по Дизайну-Б — staleness на ОБА цен-фида, decimals-скейлинг, направление округления mulDiv (Floor, protocol-safe), CEI-порядок и reentrancy (buy/sell), проводка ролей (MINTER только Exchange, нет adminTransfer/BURNER), allowance-gated burn. + сверка эквивалентности перегруппированной формулы (Отклонение 3).
2. **4 нита:** фиксить сейчас отдельным раундом, или свести с твоими находками в ОДИН фикс-раунд (моя рекомендация — один)?
3. **Имя ветки:** оставляем `pr-1-oltin-v3` или переименовать в `feature/pr1-onchain-por` (спека)?
4. **CI:** влить `chore/ci-hardening` в PR-1 (иначе «зелёный CI» не гоняет новые сьюты — §7 вводит в заблуждение), или отдельным PR?
5. **Escrow вывода (§10-Q2)** — отложено в PR-4 (решающее правило спеки). Подтверждаешь?

## Где смотреть
Ветка `pr-1-oltin-v3` @ `acfd102`; файлы — список выше; инварианты — спека §5 (Дизайн-Б). Прогон: `cd contracts && nvm use 20 && npx hardhat test` (unit-тесты идут на hardhat-network, zksolc не нужен; zksolc нужен только для compile/deploy — тоже Node 20).
