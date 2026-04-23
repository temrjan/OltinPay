# Security Policy

## Reporting a Vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Report privately to: **<x.temrjan@gmail.com>**

Include:

- Affected component (smart contracts / backend API / webapp / bot)
- Steps to reproduce
- Impact assessment
- Your preferred contact channel for follow-up (email is default; PGP or
  Signal can be arranged for sensitive reports)

We aim to acknowledge reports within 72 hours.

## Scope

OltinPay is currently a **DEMO** — tokens have no monetary value, and
mainnet contracts are not yet deployed. The following components are in
scope for security review:

- Smart contracts in `contracts/` (zkSync Era Sepolia)
- Backend API at `api.oltinpay.com`
- Telegram Mini App at `app.oltinpay.com`
- Telegram bot (with focus on handling of user secrets and wallet data)

## Out of Scope

- Rate limiting and volumetric DoS on public endpoints (known limitation
  of the current DEMO stage)
- Issues that require physical access to a user's device
- Vulnerabilities in third-party dependencies that are already tracked
  publicly and have not yet been patched upstream
- Social engineering of project maintainers, contributors, or users
- Findings on testnet-only contracts that cannot be reproduced on
  mainnet-analogous configurations

## Safe Harbor

Security research conducted in good faith that:

- Makes a reasonable effort to avoid harm to users, data, and services
- Does not access, modify, or exfiltrate user data beyond what is
  necessary to demonstrate the vulnerability
- Gives the maintainer a reasonable opportunity to remediate before
  any public disclosure

will not be pursued legally. Responsible disclosure is appreciated and
will be credited in release notes unless the reporter prefers anonymity.

## Encrypted Communication

For reports that warrant end-to-end encryption, send an initial email
requesting an encrypted channel, and we will coordinate PGP or Signal
as appropriate.
