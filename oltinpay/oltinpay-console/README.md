# OltinChain Console

Two surfaces for the OltinChain tokenized-gold demo, reading the PR-2 API:

- **Public Proof-of-Reserve dashboard** (`/`) — no auth. Live coverage ratio,
  attested reserve (= mint cap), OLTIN supply, price, the attestation feed and
  contract links. Auto-polls every 7s so the reserve gate is visible **live**:
  lower the attestation in the panel → coverage and mint-cap drop on screen.
- **Bank operator panel** (`/bank`) — operator-gated. Post reserve attestations
  and FX rates, confirm fiat deposits (mint UZD), and confirm/reject withdrawals
  (burn UZD).

## Architecture

- **No API changes.** The Console only consumes existing endpoints.
- **Same-origin proxy** for public reads: the browser polls `/api/por`,
  `/api/rates`, `/api/history` (Next.js route handlers) which fetch the API
  server-side, so there is no CORS dependency and `API_URL` stays server-side.
- **Server-side HMAC signing** for the bank panel: `/api/bank/*` route handlers
  hold `BANK_HMAC_SECRET`, sign each request (`HMAC-SHA256(secret,
  body‖ts‖nonce)`, matching the API byte-for-byte), and forward it. The secret
  never reaches the browser (verified in CI-style: absent from `.next/static`).
  The signing layer is unit-tested against a golden vector from the API's
  `bank/deps.compute_signature`, and for the sign-then-forward-same-bytes
  invariant.
- **Operator gate** is checked **server-side on every bank request**
  (`CONSOLE_OPERATOR_PASSWORD`), so it cannot be bypassed from the client.

## Environment

Copy `.env.example` to `.env` and fill in:

| Var | Scope | Purpose |
| --- | --- | --- |
| `API_URL` | server | Base URL of the OltinChain API (PR-2), e.g. `https://api.example.com/api/v1`. |
| `BANK_HMAC_SECRET` | server | Shared with the API's `BANK_HMAC_SECRET`; signs bank requests. |
| `CONSOLE_OPERATOR_PASSWORD` | server | Gates `/bank`. **Must be ≥24 random chars** — see Security. |

None are `NEXT_PUBLIC_*` — all stay server-side.

## Security

The `/bank` operator gate is checked server-side on every request but has **no
rate-limiting or lockout** — anyone who can reach `/api/bank/*` could brute-force
the password at network speed. On a testnet demo there are no currency values
behind the gate (Sepolia UZD/OLTIN), so the impact is spam, not loss. The
accepted mitigation (ratified) is a **high-entropy password**, a deploy
invariant:

- Set `CONSOLE_OPERATOR_PASSWORD` to **≥24 random characters**
  (e.g. `openssl rand -base64 24`) — brute-force is then infeasible with no
  rate-limiter.
- An in-memory rate-limiter is deliberately NOT built: on serverless (Vercel)
  it is per-instance and ineffective (same class as the API's single-writer
  nonce store); a real one needs KV/Redis — over-engineering for a testnet demo.
- Optional belt-and-suspenders: Vercel deployment protection / edge auth in
  front of `/bank` (deploy-level, no code).

## Develop

```bash
npm ci
npm run dev        # http://localhost:3000  (needs a reachable API_URL)
npm test           # signing + operator-gate unit tests
npm run typecheck && npm run lint && npm run build
```

## Deploy

Primary target is **Vercel** (a server runtime is required — the bank route
handlers sign server-side, so this is not a static export). Set the three env
vars above as server-side environment variables. A `Dockerfile` is included for
self-hosting.

> The dashboard only shows something once the **live demo stack** is up (spec E4):
> the API deployed **single-worker**, the XAU keeper running, an initial FX and
> reserve attestation posted, and the UZD treasury seeded.

## Demo script (the "nail")

1. Open `/` — note the coverage ratio and mint cap.
2. In `/bank`, post a **lower** attestation (fewer grams).
3. Watch `/` — coverage and mint cap drop within a poll cycle. The on-chain
   reserve gate is real and live, not a slide.
