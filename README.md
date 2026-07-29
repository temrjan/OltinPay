# OltinPay

On-chain infrastructure for issuing a **gold-indexed payment obligation** — smart contracts, a
non-custodial wallet, a Telegram Mini App, swap and staking. Built for a bank or payment
organisation to run under its own licence: **the partner is the issuer, this repository is the
machinery.**

The issuer sets, on-chain, the amount of coverage it is willing to stand behind. The contracts then
make it arithmetically impossible to issue beyond that amount. What the coverage consists of — gold,
liquidity, capital — is the issuer's decision and sits outside this system.

**Status: testnet demonstration.** zkSync Era Sepolia, chain id 300. Tokens carry no monetary value.
No external security audit has been performed. See [Limitations](#limitations) — worth reading before
anything else here.

---

## What you can verify without trusting us

Every claim below resolves to an address or a command.

| Contract | Address | Role |
|---|---|---|
| OLTIN | [`0x906bcf6c…B3A5`](https://sepolia.explorer.zksync.io/address/0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5) | the gold-indexed obligation |
| Coverage attestor | [`0x9413F602…7d1B`](https://sepolia.explorer.zksync.io/address/0x9413F60295dcf7D81fcb69eE256029900B107d1B) | issuance ceiling, posted by the issuer |
| Exchange | [`0x99D733E6…d1c9`](https://sepolia.explorer.zksync.io/address/0x99D733E64eb60c3B3D5f3DeDe4CC4adC92BCd1c9) | swap against the treasury at the oracle rate |
| Staking | [`0xD3b6ffd1…1fAa`](https://sepolia.explorer.zksync.io/address/0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa) | term deposit, 7-day per-lot lock |
| UZD | [`0x51232fd0…02aA`](https://sepolia.explorer.zksync.io/address/0x51232fd0065bD2ca50551761Acef476E3CDf02aA) | UZS-denominated settlement token |

Full deployment record, retired addresses included: [`docs/DEPLOYMENTS.md`](docs/DEPLOYMENTS.md).

Running system: the Mini App at [app.oltinpay.com](https://app.oltinpay.com) and an interactive API
reference for partner integration at [api.oltinpay.com/scalar](https://api.oltinpay.com/scalar).

Read the ceiling and the issuance yourself (foundry's `cast`, or any JSON-RPC client):

```bash
# issuance ceiling, in grams — Attestor.latestRoundData()
cast call 0x9413F60295dcf7D81fcb69eE256029900B107d1B \
  "latestRoundData()(uint80,int256,uint256,uint256,uint80)" \
  --rpc-url https://sepolia.era.zksync.dev      # second value is the ceiling, in grams

# tokens issued — OLTIN.totalSupply()
cast call 0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5 "totalSupply()(uint256)" \
  --rpc-url https://sepolia.era.zksync.dev      # 18 decimals
```

Coverage is the ratio of the two. Public, permissionless to read, and it changes the moment the
issuer changes it — not once a quarter.

**Source is published on the explorer.** Every contract above is verified — open any address and the
Solidity is there, compiled with `zkVM-0.8.24-1.0.1`, matching this repository byte for byte. You do
not have to take the invariants below on trust; read the code at the address that holds the funds.

---

## Invariants the code enforces

These are the load-bearing guarantees. Each names the contract and function that enforces it, so the
claim can be checked against source rather than taken on trust.

**Issuance cannot exceed attested coverage.**
`OltinTokenV3.mint` reverts unless `totalSupply() + amount <= attestation × scale`. The check lives
in the token contract, not in an application, so it cannot be bypassed through the API, the wallet,
or by us.

**Stale coverage stops issuance automatically.**
The same function requires the attestation to be no older than `maxAgeReserve` (3600 s). If the
issuer stops attesting, minting halts within the hour on its own. The system fails closed.

**The issuer can tighten instantly and unilaterally.**
Posting a lower number lowers the ceiling in the same block. Already-issued tokens are untouched;
new issuance stops. No cooperation from us is required.

**A stake cannot be withdrawn before its term — by anyone.**
`OltinStaking.unstake` skips lots whose `lockedUntil` is in the future and reverts if the request
exceeds the unlocked principal. There is no emergency exit, no admin unlock, no rescue path.

**The administrator cannot touch a user's principal.**
`OltinStaking.withdrawRewardPool` is bounded by `amount <= rewardPool`. Staked principal is tracked
separately and is unreachable from every administrative function. Custody is enforced by code, not
by policy.

**Exactly one address can mint, and it is a contract.**
`MINTER_ROLE` on OLTIN has been granted twice and revoked once; enumerating `RoleGranted` and
`RoleRevoked` events leaves a single current holder — the Exchange. No human key can issue tokens.
Verify by replaying those events against the token address.

**Private keys never leave the client.**
The wallet derives a BIP39 seed on device, encrypts it with scrypt (N = 2¹⁷) + AES-256-GCM and
stores the ciphertext in Telegram Cloud Storage. The backend stores only a public address. Every
state-changing transaction is signed on device.

---

## How the money moves

```
fiat (UZS) ──▶ UZD ──▶ OLTIN ──┬──▶ P2P transfer
  deposit      mint    Exchange │
                       (mint)   └──▶ Staking, 7-day lock ──▶ reward, paid from a funded pool

OLTIN ──▶ UZD ──▶ fiat
Exchange  treasury  withdrawal
 (burn)
```

Buying mints OLTIN against the attested ceiling; selling burns it and pays UZD from the Exchange's
own treasury. Rewards come from a pre-funded pool and are never minted — issuance is not used to
manufacture yield.

---

## Repository layout

```
contracts/                     Solidity 0.8.24, hardhat-zksync
  contracts/
    OltinTokenV3.sol           the obligation token — attested-coverage gate on mint
    Attestor.sol               coverage feed (also carries the XAU and UZS rates)
    Exchange.sol               swap against treasury; immutable feeds, no admin functions
    OltinStaking.sol           per-lot 7-day lock, pull-based rewards
    UZD.sol                    settlement token
    OltinPaymaster.sol         sponsored-gas paymaster (proven on chain, not wired into the demo)
  test/                        204 test cases across 9 files
  test-vm/                     paymaster e2e against a local zkSync VM node

oltinpay/
  oltinpay-api/                FastAPI backend — balances, transfers, PoR, indexer, bank rails
  oltinpay-webapp/             Next.js Mini App — wallet, exchange, staking
  oltinpay-console/            operator console — reserve dashboard, bank panel
  oltinpay-bot/                aiogram bot

ops/oltinpay-keeper/           standalone feed keeper (stdlib JSON-RPC, systemd timer)
docs/                          architecture, deployment record, deploy runbook
.github/workflows/             CI — one gated workflow per surface
```

---

## Stack, and why

| Layer | Choice | Reason |
|---|---|---|
| Network | zkSync Era (Sepolia) | transaction cost low enough that per-user on-chain settlement is viable |
| Contracts | Solidity 0.8.24, OpenZeppelin AccessControl | no proxy, no upgrade path — see Limitations for what that costs |
| Wallet | BIP39 + scrypt (N = 2¹⁷) + AES-256-GCM, client-side | the issuer never holds customer keys, which removes a class of custody obligation |
| Frontend | Next.js 16.1.4, React 19.2.3, viem 2.48.2 | viem gives typed contract calls and native zkSync support |
| Backend | FastAPI ≥ 0.115, SQLAlchemy 2.0, Python 3.12 | reads chain state; holds no keys to user funds |
| Database | PostgreSQL 16 | advisory locks serialise the check-then-act paths |
| Feed keeper | Python stdlib + eth-account, systemd timer | no project imports, so it cannot break when the application changes |

---

## Tests and CI

```bash
cd contracts                 && npm ci && npm test                       # 204 cases, 9 files
cd oltinpay/oltinpay-webapp  && npm ci && npm test                       # 36 tests

cd oltinpay/oltinpay-api     && uv sync --locked --extra dev
uv run pytest -q                                                         # 163 passed, 2 skipped
TEST_PG_URL=postgresql+asyncpg://user:pass@localhost/db uv run pytest -q  # 165 passed

# The two skipped tests are the advisory-lock concurrency guards. They need a real
# Postgres and skip silently without one — which is exactly how the race they guard
# against originally shipped. CI always provides the service, so they always run there.
```

CI runs on **every pull request**, not after merge — four gated workflows in `.github/workflows/`,
one per surface (api, webapp, console, contracts), each with a `paths` filter so a change to one
surface does not run the others. A fifth workflow deploys and is `workflow_dispatch` only.

Deliberate properties of the pipeline, each checkable in the workflow files:

- **No suppressed gates.** No `|| true`, no `continue-on-error` on a check step. A red gate fails the build.
- **Actions pinned by commit SHA**, with SHA pinning required at the repository level — a tag can be moved by whoever owns it, a commit hash cannot.
- **Minimal `permissions`** declared per workflow; the deploy workflow runs with `permissions: {}`.
- **Installs from lockfiles** (`npm ci`, `uv sync --locked`) plus an explicit lockfile-drift check.
- **A real Postgres service** in the API job, because the advisory-lock regression tests skip silently on SQLite — which is exactly how the race they guard against originally shipped.
- **The full suite runs**, never a pinned list of files, so a new test file gates CI automatically.

Contracts get a second job against a local zkSync VM node, because account abstraction cannot be
exercised in the plain EVM test environment.

---

## Limitations

Stated plainly, because they are what a reader needs in order to weigh the rest.

- **Testnet only.** zkSync Era Sepolia. Tokens have no monetary value.
- **No external security audit.** An adversarial internal review process is in place and has caught
  fund-drain, authentication-bypass, reserve-race and double-issuance defects in review. That is not
  a substitute for an independent audit, and none has been done.
- **Contracts are immutable.** No proxy, no upgrade path, and `Exchange` has no administrative
  function at all — not even a treasury sweep. Deliberate: nobody can quietly change the rules. The
  cost is that any fix means a new contract and a migration of live positions.
- **Administrative control sits on a single EOA**, and it carries a pause power. `stake`, `unstake`
  and `claim` are all `whenNotPaused`, so the holder of `PAUSER_ROLE` can freeze the staking product
  entirely — deposits, withdrawals and reward claims alike. `withdrawRewardPool` is *not* pause-gated,
  so the reward pool remains withdrawable by the admin while users are frozen. The admin still cannot
  reach staked principal (next invariant), but this asymmetry is real and worth knowing. A
  multi-signature arrangement is the obvious next step and has not been made.
- **The indexer is a last-N block poller** and is not reorg-safe. Adequate on a testnet, not a
  settlement-grade design.
- **UZD carries no on-chain reserve constraint.** `UZD.mint` is role-gated only. It is a settlement
  token issued by the operator, not a reserve-backed stablecoin.

---

## Local development

```bash
# Backend
cd oltinpay/oltinpay-api
cp .env.example .env                     # fill in values; never commit this file
docker compose up -d postgres redis
uv sync --extra dev
alembic upgrade head
uv run uvicorn src.main:app --reload

# Frontend
cd oltinpay/oltinpay-webapp
npm ci && npm run dev

# Contracts
cd contracts
npm ci && npx hardhat compile && npm test
```

---

## Security

- Secrets live in `.env` only. Private keys, tokens and credentialed RPC URLs are never committed;
  `.gitignore` covers `.env*`, and secret-scanning push protection is enabled on this repository.
- The deployer key is held locally and is never placed on a server. The server-side signer holds one
  minting role and an ETH balance for gas — no administrative role, and no access to user funds.
- Vulnerability reports: see [`SECURITY.md`](SECURITY.md).

---

## Licence

See [`LICENSE`](LICENSE) and [`NOTICE.md`](NOTICE.md).

Operating this system commercially requires licensing by the national regulator —
[NAPP](https://napp.uz/ru/pages/service-providers) determines which licence applies. This repository
is the infrastructure; the licence, the fiat rails and the coverage are the partner's.
