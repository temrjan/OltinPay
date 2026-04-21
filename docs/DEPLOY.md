# OltinPay — Deployment

> CI/CD pipeline: GitHub push to `main` → GitHub Actions → SSH deploy on `7demo` server.

---

## Pipeline overview

```
git push origin main
   └── .github/workflows/
       ├── api.yml        — ruff + mypy + pytest
       ├── webapp.yml     — tsc + next lint
       ├── contracts.yml  — hardhat test (UZD + OltinStaking)
       └── deploy.yml     — SSH into 7demo, git pull, docker compose up
```

CI runs in parallel (api / webapp / contracts) on every push to `main` and every pull request touching the relevant paths. Deploy runs only on `main` and waits for nothing — GitHub doesn't chain `deploy.yml` after the other workflows. If you want deploy gated by green CI, convert deploy to `workflow_run` triggered by `api.yml`/`webapp.yml`/`contracts.yml` success.

---

## First-time server setup

The old `/opt/oltinchain/` deployment still holds the running `oltinpay-webapp` container. Replace it cleanly once:

```bash
ssh 7demo

# 1. Stop and remove the legacy stack
cd /opt/oltinchain
docker compose down --remove-orphans
# (don't delete the directory yet — back up the .env first)
cp .env /root/oltinpay.env.backup

# 2. Clone v2 into its new home
git clone https://github.com/temrjan/OltinPay.git /opt/oltinpay
cd /opt/oltinpay

# 3. Bring the .env over and edit as needed
cp /root/oltinpay.env.backup .env
nano .env   # verify DB URL, secrets, contract addresses match docker-compose.yml

# 4. First build + up
docker compose up -d --build

# 5. Verify
docker ps | grep oltinpay
docker logs oltinpay-api --tail 50
curl -s https://api.oltinpay.com/health

# 6. Remove the old dir once you're happy
rm -rf /opt/oltinchain
```

Caddy already routes `api.oltinpay.com` → `oltinpay-api:8000` and `app.oltinpay.com` → `oltinpay-webapp:3000` (see `/root/server/infra/Caddyfile`). No infra changes needed.

---

## GitHub Secrets

Add these in **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value | Notes |
|---|---|---|
| `DEPLOY_SSH_KEY` | Full private key (PEM text) of a user that can `ssh root@7demo` and run `docker compose` | Generate a dedicated deploy key: `ssh-keygen -t ed25519 -f deploy_key -N ""` on your laptop, add the **public** half to `/root/.ssh/authorized_keys` on the server, paste the **private** half into this secret |
| `DEPLOY_HOST` | Hostname or IP of the server | e.g. `vitrina.example.com` or the public IP |
| `DEPLOY_USER` | SSH login user | usually `root` |

Optionally add an **Environment** called `production` with a required reviewer to gate deploys (`environment: production` in `deploy.yml` already references it).

---

## Local verification before push

Run the same checks CI runs, to avoid red runs:

```bash
# API
cd oltinpay/oltinpay-api
pip install -e ".[dev]"
ruff check src/
mypy --ignore-missing-imports src/infrastructure/ src/balances/ src/users/schemas.py src/users/router.py src/users/service.py src/main.py
pytest tests/test_rpc.py tests/test_blockchain.py tests/test_users_wallet.py tests/test_balances_onchain.py tests/test_auth.py

# Webapp
cd ../oltinpay-webapp
npm ci
npx tsc --noEmit
npx next lint

# Contracts
cd ../../contracts
npm ci
npx hardhat compile
npx hardhat test test/UZD.test.ts test/OltinStaking.test.ts
```

---

## Rollback

Deploy script does `git reset --hard origin/main` — no revert path on the server. To roll back:

```bash
git revert <bad-commit>
git push origin main   # triggers CI + deploy again
```

Or manually:

```bash
ssh 7demo "cd /opt/oltinpay && git reset --hard <good-sha> && docker compose up -d --build"
```

---

## Troubleshooting

- **Deploy fails at `docker compose up`** — check `.env` on the server has all required vars (DB URL, secret keys, contract addresses). The workflow prints `docker logs` output; follow the first error.
- **SSH auth fails** — confirm `DEPLOY_SSH_KEY` was pasted including the `-----BEGIN ... KEY-----` and `-----END ... KEY-----` lines, no extra whitespace.
- **Webapp still serves old build** — the deploy runs `docker compose up -d --build`; if nothing changed in the webapp path and Docker thinks layers are cached, force rebuild: `ssh 7demo "cd /opt/oltinpay && docker compose build --no-cache oltinpay-webapp && docker compose up -d oltinpay-webapp"`.
- **CI pytest fails** — inspect the run logs. If tests pass locally but fail on CI, it's usually a missing env var or a Python version mismatch (CI uses 3.12).

---

## What's NOT deployed by this pipeline

- **Smart contracts** — deployed manually via `contracts/scripts/deploy.sh` (see `docs/PROGRESS.md`). No automation on purpose: contract deployment is irreversible and costs real (or testnet) gas.
- **alembic migrations** — not auto-applied by the Docker image. Run on the server after deploy:
  ```bash
  ssh 7demo "cd /opt/oltinpay && docker compose exec oltinpay-api alembic upgrade head"
  ```
  (We can move this into the `oltinpay-api` container entrypoint later if we want.)
