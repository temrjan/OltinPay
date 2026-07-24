import { expect } from "chai";
import {
  allowanceWithMargin,
  classifyMining,
} from "../scripts/smoke-gasless";

describe("gasless smoke helpers", function () {
  it("should size the allowance as quote x margin, rounded up", function () {
    // 258679734705000 x 1.2 = 310415681646000 exactly.
    expect(allowanceWithMargin(258679734705000n, 12000n)).to.equal(310415681646000n);
    // Rounds UP, never down: 1 wei of quote at any margin stays >= quote.
    expect(allowanceWithMargin(3n, 12000n)).to.equal(4n); // 3*1.2=3.6 -> 4
    expect(allowanceWithMargin(100n, 10000n)).to.equal(100n); // margin 1.0 = exact
  });

  it("should distinguish mined / reverted / silently-refused outcomes", function () {
    expect(classifyMining(1, false)).to.deep.equal({ status: "mined" });
    expect(classifyMining(0, false)).to.deep.equal({ status: "reverted" });
    // The dangerous one: no receipt at all, we stopped waiting.
    expect(classifyMining(null, true)).to.deep.equal({ status: "silentlyRefused" });
    expect(() => classifyMining(null, false)).to.throw();
  });
});
