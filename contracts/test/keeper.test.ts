import { expect } from "chai";
import {
  decidePost,
  decideReservePost,
  checkSourceAge,
  chainNowSeconds,
  parseCbuResponse,
  parseDecimalToScaledInt,
  cbuRateAgeDays,
  parsePositiveInt,
  parsePricesBySymbolResponse,
  decideGoldPrice,
  checkCbuAge,
  type TokenUsdPrice,
  type GoldPriceInput,
  type BlockTimestampProvider,
  type DecideInput,
} from "../scripts/keeper-lib";

describe("keeper decidePost", function () {
  const base: DecideInput = {
    current: 4000_00000000n, // $4,000.00000000 at 8 decimals
    currentUpdatedAt: 1_000_000n,
    next: 4000_00000000n,
    now: 1_000_000n + 100n,
    minDelta: 0n,
    maxJumpBps: 1000n, // 10%
    heartbeatAge: 1800n,
  };

  it("should post the first reading when the feed is empty (current == 0)", function () {
    const d = decidePost({ ...base, current: 0n, currentUpdatedAt: 0n });
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/first post/);
  });

  it("should skip when the value is unchanged and the on-chain reading is fresh", function () {
    const d = decidePost(base);
    expect(d.action).to.equal("skip");
    expect(d.reason).to.match(/unchanged/);
  });

  it("should post a heartbeat when the value is unchanged but the on-chain reading approaches maxAge", function () {
    const d = decidePost({ ...base, now: base.currentUpdatedAt + 1800n });
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/heartbeat/);
  });

  it("should post when the value moved within the jump guard", function () {
    const d = decidePost({ ...base, next: base.current + 100_00000000n }); // +2.5%
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/deviation 250bps/);
  });

  it("should refuse a wild deviation beyond the jump guard instead of relaying it", function () {
    const d = decidePost({ ...base, next: base.current * 2n }); // +100%
    expect(d.action).to.equal("refuse");
    expect(d.reason).to.match(/wild deviation/);
  });

  it("should refuse a wild deviation even when the heartbeat is due — guard beats heartbeat", function () {
    const d = decidePost({
      ...base,
      next: base.current * 2n,
      now: base.currentUpdatedAt + 3600n, // heartbeat is due
    });
    expect(d.action).to.equal("refuse");
    expect(d.reason).to.match(/wild deviation/);
  });

  it("should post a heartbeat when the age is exactly HEARTBEAT_AGE (inclusive threshold)", function () {
    const exact = decidePost({ ...base, now: base.currentUpdatedAt + 1800n });
    expect(exact.action).to.equal("post");
    const justUnder = decidePost({ ...base, now: base.currentUpdatedAt + 1799n });
    expect(justUnder.action).to.equal("skip");
  });
});

describe("keeper decideReservePost", function () {
  const base = {
    current: 5000n,
    currentUpdatedAt: 1_000_000n,
    next: 5000n,
    now: 1_000_000n + 100n,
    heartbeatAge: 1800n,
    maxJumpBps: 1000n, // 10%
    confirm: undefined as string | undefined,
  };

  it("should post the first reserve attestation without a guard (seed)", function () {
    const d = decideReservePost({ ...base, current: 0n, currentUpdatedAt: 0n });
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/first reserve/);
  });

  it("should post a small reserve change within the guard", function () {
    const d = decideReservePost({ ...base, next: 5250n }); // +5%
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/within guard/);
  });

  it("should refuse a reserve change beyond the guard without RESERVE_CONFIRM", function () {
    const d = decideReservePost({ ...base, next: 7500n }); // +50%
    expect(d.action).to.equal("refuse");
    expect(d.reason).to.match(/RESERVE_CONFIRM/);
  });

  it("should post a reserve change beyond the guard when RESERVE_CONFIRM equals the new value", function () {
    const d = decideReservePost({ ...base, next: 7500n, confirm: "7500" });
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/confirmed/);
  });

  it("should refuse when RESERVE_CONFIRM does not match the new value exactly", function () {
    const d = decideReservePost({ ...base, next: 7500n, confirm: "7501" });
    expect(d.action).to.equal("refuse");
  });

  it("should heartbeat an unchanged reserve when the reading approaches maxAge", function () {
    const d = decideReservePost({ ...base, now: base.currentUpdatedAt + 1800n });
    expect(d.action).to.equal("post");
    expect(d.reason).to.match(/heartbeat/);
  });
});

describe("keeper checkSourceAge", function () {
  const maxAge = 259200n; // 72h
  const warnAge = 82800n; // 23h — above the Chainlink XAU heartbeat (22h20m)

  it("should be ok for an ordinary quiet weekday reading (5h old)", function () {
    expect(checkSourceAge(5n * 3600n, maxAge, warnAge).level).to.equal("ok");
  });

  it("should relay a weekend-frozen reading (50h old) with a warning, not a refusal", function () {
    const v = checkSourceAge(50n * 3600n, maxAge, warnAge);
    expect(v.level).to.equal("warn");
  });

  it("should refuse a broken source (older than 72h)", function () {
    const v = checkSourceAge(73n * 3600n, maxAge, warnAge);
    expect(v.level).to.equal("refuse");
  });
});

describe("keeper chainNowSeconds", function () {
  it("should read now from the block timestamp, not the local clock", async function () {
    // Local clock is deliberately skewed days away from the block time.
    const blockTs = 1_800_000_000;
    const stub: BlockTimestampProvider = {
      getBlock: async (tag: string) => {
        expect(tag).to.equal("latest");
        return { timestamp: blockTs };
      },
    };
    const now = await chainNowSeconds(stub);
    expect(now).to.equal(BigInt(blockTs));
    expect(now).to.not.equal(BigInt(Math.floor(Date.now() / 1000)));
  });
});

describe("keeper CBU parsing", function () {
  it("should parse a valid CBU response into a scaled 8-decimal value", function () {
    const body = [{ Code: "840", Ccy: "USD", Rate: "12048.84", Date: "23.07.2026" }];
    const { rateRaw, dateRaw } = parseCbuResponse(body);
    expect(dateRaw).to.equal("23.07.2026");
    expect(parseDecimalToScaledInt(rateRaw, 8)).to.equal(12048_84000000n);
  });

  it("should reject malformed CBU payloads instead of relaying them", function () {
    expect(() => parseCbuResponse({})).to.throw();
    expect(() => parseCbuResponse([])).to.throw();
    expect(() => parseCbuResponse([{ Rate: 12048.84, Date: "23.07.2026" }])).to.throw();
    expect(() => parseDecimalToScaledInt("0", 8)).to.not.throw();
    expect(() => parseDecimalToScaledInt("abc", 8)).to.throw();
    expect(() => parseDecimalToScaledInt("-5", 8)).to.throw();
    expect(() => parseDecimalToScaledInt("1.123456789", 8)).to.throw();
  });

  it("should accept a Monday reading dated last Friday (3 days old, guard is 7 days)", function () {
    // Monday 27.07.2026, rate dated Friday 24.07.2026.
    const days = cbuRateAgeDays("24.07.2026", new Date(Date.UTC(2026, 6, 27, 9, 0, 0)));
    expect(days).to.equal(3);
    expect(days <= 7).to.be.true;
  });

  it("should refuse a rate older than 7 days as a broken API", function () {
    const days = cbuRateAgeDays("15.07.2026", new Date(Date.UTC(2026, 6, 23, 9, 0, 0)));
    expect(days).to.equal(8);
    expect(days <= 7).to.be.false;
  });
});

describe("keeper parsePositiveInt (RESERVE_GRAMS)", function () {
  it("should parse a plain gram count", function () {
    expect(parsePositiveInt("5000", "RESERVE_GRAMS")).to.equal(5000n);
  });

  it("should reject non-integer, negative and zero values", function () {
    expect(() => parsePositiveInt("5000.5", "RESERVE_GRAMS")).to.throw();
    expect(() => parsePositiveInt("-5", "RESERVE_GRAMS")).to.throw();
    expect(() => parsePositiveInt("0", "RESERVE_GRAMS")).to.throw();
    expect(() => parsePositiveInt("abc", "RESERVE_GRAMS")).to.throw();
  });
});

describe("keeper parsePricesBySymbolResponse (Alchemy)", function () {
  it("should parse a live-shaped by-symbol response keeping only USD quotes", function () {
    const body = {
      data: [
        { symbol: "PAXG", prices: [{ currency: "usd", value: "4037.4", lastUpdatedAt: "2026-07-23T18:13:20.037Z" }] },
        { symbol: "XAUT", prices: [{ currency: "usd", value: "4043.4", lastUpdatedAt: "2026-07-23T18:13:20.566Z" }] },
      ],
    };
    const out = parsePricesBySymbolResponse(body);
    expect(out).to.have.length(2);
    expect(out[0]).to.deep.equal({ symbol: "PAXG", valueRaw: "4037.4", lastUpdatedAt: "2026-07-23T18:13:20.037Z" });
  });

  it("should reject malformed payloads instead of trusting them", function () {
    expect(() => parsePricesBySymbolResponse(null)).to.throw();
    expect(() => parsePricesBySymbolResponse([])).to.throw();
    expect(() => parsePricesBySymbolResponse({})).to.throw();
    expect(parsePricesBySymbolResponse({ data: [{ symbol: "PAXG", prices: [{ currency: "usdt", value: "1" }] }] })).to.have.length(0);
  });
});

describe("keeper decideGoldPrice (median + chainlink liveness detector)", function () {
  const paxg: TokenUsdPrice = { symbol: "PAXG", valueRaw: "4037.4", lastUpdatedAt: "2026-07-23T18:13:20.037Z" };
  const xaut: TokenUsdPrice = { symbol: "XAUT", valueRaw: "4043.4", lastUpdatedAt: "2026-07-23T18:13:20.566Z" };
  const base: GoldPriceInput = {
    prices: [paxg, xaut],
    nowSeconds: 1784831000n, // ~18:23 UTC 2026-07-23, quotes are ~10 min old
    maxTokenPriceAge: 3600n,
    minSaneUsd: 100_00000000n,
    maxSaneUsd: 100000_00000000n,
    chainlinkAgeSeconds: 3600n,
    chainlinkFreshAge: 82800n,
  };

  it("should post the median (average of two) when both sources are valid", function () {
    const d = decideGoldPrice(base);
    expect(d.action).to.equal("post");
    if (d.action === "post") expect(d.price).to.equal(4040_40000000n); // (4037.4 + 4043.4) / 2
  });

  it("should post a single valid source with a degraded warning", function () {
    const d = decideGoldPrice({ ...base, prices: [paxg] });
    expect(d.action).to.equal("post");
    if (d.action === "post") {
      expect(d.price).to.equal(4037_40000000n);
      expect(d.reason).to.match(/degraded to single source PAXG/);
    }
  });

  it("should refuse as 'we are broken' when tokens are dead but chainlink is fresh", function () {
    const d = decideGoldPrice({ ...base, prices: [], chainlinkAgeSeconds: 3600n });
    expect(d.action).to.equal("refuse");
    expect(d.reason).to.match(/we are broken/i);
  });

  it("should refuse as 'infra outage' when tokens are dead and chainlink is stale or unreadable", function () {
    const stale = decideGoldPrice({ ...base, prices: [], chainlinkAgeSeconds: 90000n });
    expect(stale.action).to.equal("refuse");
    expect(stale.reason).to.match(/infra outage/i);
    const unreadable = decideGoldPrice({ ...base, prices: [], chainlinkAgeSeconds: undefined });
    expect(unreadable.action).to.equal("refuse");
    expect(unreadable.reason).to.match(/infra outage/i);
  });

  it("should refuse when the shared L1 clock is unavailable, even with live token quotes", function () {
    // Freshness is unprovable without a shared clock: an unreadable L1 block
    // time must NOT fail open into "everything is fresh forever".
    const d = decideGoldPrice({ ...base, nowSeconds: undefined });
    expect(d.action).to.equal("refuse");
    expect(d.reason).to.match(/clock/i);
  });

  it("should accept a quote stamped slightly ahead of the block clock (API clock skew)", function () {
    // Prices API stamps quotes at response time; its clock can run ahead of
    // the latest L1 block timestamp by seconds. A near-future quote is fresh,
    // not garbage.
    const futureQuote: TokenUsdPrice = { symbol: "PAXG", valueRaw: "4037.4", lastUpdatedAt: "2026-07-23T18:25:00.000Z" };
    // Quote stamped 18:25:00; block clock ~1 minute behind it.
    const pastBlock = BigInt(Math.floor(Date.UTC(2026, 6, 23, 18, 24, 0) / 1000));
    const d = decideGoldPrice({ ...base, prices: [futureQuote], nowSeconds: pastBlock });
    expect(d.action).to.equal("post");
    if (d.action === "post") expect(d.price).to.equal(4037_40000000n);
  });

  it("should discard out-of-range and stale quotes instead of relaying them", function () {
    const crazy: TokenUsdPrice = { symbol: "PAXG", valueRaw: "5", lastUpdatedAt: paxg.lastUpdatedAt };
    const d1 = decideGoldPrice({ ...base, prices: [crazy, xaut] });
    expect(d1.action).to.equal("post");
    if (d1.action === "post") expect(d1.price).to.equal(4043_40000000n); // crazy discarded
    const staleQuote: TokenUsdPrice = { symbol: "PAXG", valueRaw: "4037.4", lastUpdatedAt: "2026-07-22T18:13:20.000Z" };
    const d2 = decideGoldPrice({ ...base, prices: [staleQuote] });
    expect(d2.action).to.equal("refuse"); // stale quote = dead source
  });
});

describe("keeper checkCbuAge (P1-E: warn-and-relay)", function () {
  it("should warn and relay a 5-day-old rate (holidays), not refuse", function () {
    const v = checkCbuAge(5, 3, 14);
    expect(v.level).to.equal("warn");
  });

  it("should refuse a rate older than 14 days as a broken API", function () {
    expect(checkCbuAge(15, 3, 14).level).to.equal("refuse");
  });

  it("should be ok for an ordinary 1-day-old weekday rate", function () {
    expect(checkCbuAge(1, 3, 14).level).to.equal("ok");
  });

  it("should refuse a future-dated rate", function () {
    expect(checkCbuAge(-1, 3, 14).level).to.equal("refuse");
  });
});
