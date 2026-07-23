import { expect } from "chai";
import { decidePost, type DecideInput } from "../scripts/keeper-lib";

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
