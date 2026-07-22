# ДЕЛЬТА к Гейту-2 PR-1 (фикс-раунд) — Ревьюеру на быстрый ре-ревью

> Кресло: Инженер → Ревьюеру (через Капитана). Ответ на APPROVED WITH NITS.
> Ветка `feature/pr1-onchain-por` (переименована с `pr-1-oltin-v3`), **HEAD `9eec633`** поверх `acfd102`.
> **НЕ запушено, НЕ ребейзнуто, НЕ смержено** (ребейз на main — после твоего «чисто»). Без AI-подписи.
> Дельта: `git diff acfd102..9eec633` — 9 файлов, +353/−32.

## Применено (все 12 пунктов — DONE)
| Пункт | Что сделано |
|---|---|
| **F16** (Exchange+deployV3) | `maxAgePrice` → два immutable `maxAgeXau`/`maxAgeUzs`; `_freshPrice(feed,maxAge)` на оба фида в buy И sell; конструктор 5→6 арг; deployV3 + env (MAX_AGE_XAU=3600, MAX_AGE_UZS=259200=3д, переживает выходные ЦБ) |
| **F15** (deploySecondAsset) | грант MINTER_ROLE явному minter (env SECOND_MINTER, деф deployer) + лог; второй токен больше не инертен |
| **F8** (OltinTokenV3) | кэш immutable `reserveScale=10**(18-d)`; mint: `totalSupply()+amount <= uint256(r)*reserveScale` — арифметически идентично |
| **F12/F14** (keeper-*) | max-jump гард `MAX_JUMP_BPS` (деф 10%): читает on-chain `latestRoundData`, SKIP на диком отклонении |
| **F9/F10** (keeper-*) | SKIP если не изменилось (MIN_DELTA); первый пост — безусловно |
| **F1** (Exchange.test) | 4 zero-addr ctor-реверта (oltin/uzd/xau/uzs), reason `"Zero address"` |
| **F2** (оба теста) | двусторонние границы: ==maxAge проходит / +1 ревертит (reserve, XAU, UZS); decimals==18 ок (reserveScale==1) — мутант `<=`→`<` умирает |
| **F4** (Exchange.test) | кросс-pause: paused OLTIN → buy revert (mint) и sell revert (burnFrom), EnforcedPause |
| **F13** (Exchange NatSpec) | immutable-фиды без rescue = принятое testnet-ограничение; timelock-rescue → PR-4; rescue НЕ добавлен |
| **NIT** (package.json) | скрипты deploy:v3/deploy:second/keeper:xau/keeper:uzs (legacy deploy:testnet цел) — но см. Остаток 2 |

## Доказательства
- `npx hardhat test` → **114 passing** (было 101; +13 новых). Compile чист.
- Внутренняя security-линза по изменённым контрактам (Exchange maxAge, OltinTokenV3 reserveScale, кееperы) → **0 находок**.
- Само-проверка коммита: гард цел (grep подтвердил `reserveScale`/`onlyRole(MINTER)`/`exceeds reserve`/`reserve stale` в OltinTokenV3; `maxAgeXau`/`maxAgeUzs`/`_freshPrice`×2 в Exchange), артефакты/node_modules НЕ застейджены, без AI-подписи.

## Остатки — ТРЕБУЮТ твоего действия/вердикта (честно)
1. **Мутации против `9eec633` НЕ перегнаны в этом коммите.** Fix-агент отчитался `mutationsStillRed=true`, но Finalize подтвердил гард-строки только чтением исходника, не перезапуском мутаций против финального sha. **Прошу тебя независимо перегнать m1/m2/m3 (+ границы `<=`→`<`) против `9eec633`** — это ядро, доверять на слово нельзя.
2. **`deploy:v3`/`deploy:second` НЕ разрешатся как есть:** `hardhat deploy-zksync --script` глобит `paths.deployPaths` (деф `deploy/`), а файлы в `scripts/`. Фикс: добавить `'scripts'` в `paths.deployPaths` в hardhat.config **или** перенести файлы в `deploy/`. НЕ трогал (вне тест-скоупа, без testnet не проверить). **Чинить до Sepolia-деплоя.** `keeper:*` через `hardhat run` — корректны.
3. **F16 — сознательное отклонение от спеки §5** (там был один `maxAgePrice`): разнёс на два окна, т.к. UZS (ЦБ ~раз в день) требует длиннее XAU (релей часто); один короткий порог ревертил бы buy/sell по выходным. Усиливает гард. **Прошу sign-off как осознанного отклонения.**
4. `npx tsc --noEmit` даёт pre-existing TS2339 (ethers-v6 динамическая типизация методов) по тест-файлам, включая нетронутый `Attestor.test.ts` — НЕ регрессия, реальный гейт `hardhat test` зелёный (114).

## Где смотреть
`feature/pr1-onchain-por` @ `9eec633`; `git diff acfd102..9eec633`. Инварианты — спека §5 (Дизайн-Б).
После твоего «чисто»: ребейз на актуальный main (там PR #4 CI-hardening — новые 52+ теста пойдут в CI) → push/PR. Escrow → PR-4 (подтверждено).
