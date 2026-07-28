# OltinPay feed keeper

Keeps the three on-chain attestor feeds **fresh** so `Exchange.buy/sell` and
OLTIN PoR-mint stop reverting on staleness. Each run re-posts every feed's last
on-chain answer via `Attestor.postAnswer(int256)` — the Attestor self-stamps
`updatedAt = block.timestamp`, so a re-post of the same value is a valid
heartbeat.

> The posted **value is frozen** (last answer re-posted). Real market prices are
> synced separately — see *Ops* below. This keeper only guarantees freshness,
> which is the thing the on-chain staleness checks gate on.

## Feeds

| Feed | Attestor | on-chain maxAge | heartbeat (re-post if older) | consumer |
|------|----------|-----------------|------------------------------|----------|
| XAU | `0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD` | 1 h | 25 min | Exchange price |
| RESERVE | `0x9413F60295dcf7D81fcb69eE256029900B107d1B` | 1 h | 25 min | OLTIN PoR-mint |
| UZS | `0x637347fd661cFFAE9B562aFA394A392214fa24aD` | 72 h | 18 h | Exchange price |

One systemd timer fires every 30 min and runs all three: XAU/RESERVE re-post
almost every run, UZS re-posts roughly daily. `(heartbeat + 30 min)` stays well
under each `maxAge`.

## Files (on the server, `/root/oltinpay-keeper/`)

- `keeper.py` — the keeper (eth_account + stdlib JSON-RPC only, no project imports).
- `poster.key` — **POSTER_ROLE** signing key (`0xfaFB46cC…405e`). Not the deployer key. Never leaves the box.
- `venv/` — pinned virtualenv (`requirements.txt`).
- `keeper.log` — append log; every line is `POST_OK` / `POST_FAIL(reason)` / `SKIP(fresh)`.
- systemd: `oltinpay-keeper.service` (oneshot) + `oltinpay-keeper.timer`.

## Install / update

From this directory on the server, as root:

```sh
./install.sh          # idempotent: builds venv, installs units, enables timer
```

## Verify

```sh
systemctl list-timers oltinpay-keeper.timer      # next/last run
systemctl status oltinpay-keeper.service         # last exit code
journalctl -u oltinpay-keeper.service -n 40      # recent runs
tail -f /root/oltinpay-keeper/keeper.log         # POST_OK / SKIP / POST_FAIL

# One manual run (send) or a dry run (reads + prints calldata, sends nothing):
venv/bin/python keeper.py
venv/bin/python keeper.py --dry-run
```

Freshness is confirmed on-chain: `latestRoundData().updatedAt` for each feed
should stay within `maxAge` of the current block, and a `callStatic` of
`Exchange.buy/sell` must not revert with a staleness error.

## Ops — morning of a demo

Auto re-post keeps the feeds *fresh* but *frozen*. To also show the **current**
gold price, run the real-price sync once (updates the value; the keeper then
keeps that value fresh):

```sh
cd <contracts repo>  &&  npm run keeper:all
```

## Reboot

`Persistent=true` + `OnBootSec` mean the timer catches up a missed run after a
reboot, so the box coming back up cannot leave a feed stale for long.
