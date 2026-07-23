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

  it("should skip a wild deviation beyond the jump guard instead of relaying it", function () {
    const d = decidePost({ ...base, next: base.current * 2n }); // +100%
    expect(d.action).to.equal("skip");
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
