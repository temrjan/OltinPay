/**
 * Independent integer mirror of OltinPaymaster._feeFor, shared by the plain-EVM
 * suite and the zkSync VM suite.
 *
 * It exists so a suite can assert the fee against a number derived OUTSIDE the
 * contract. Asserting `charged == quoteFee(...)` alone is a tautology: both
 * sides come from the same `_feeFor`, so a wrong formula agrees with itself.
 * Both steps round UP, mirroring the contract.
 */
import { RATE, SURCHARGE_BPS, MIN_FEE_OLTIN } from "../../config/paymasterConfig";

const ONE = 10n ** 18n;

export const ceilDiv = (a: bigint, b: bigint): bigint => (a + b - 1n) / b;

export function expectedFee(
  requiredEth: bigint,
  rate = RATE,
  surchargeBps = SURCHARGE_BPS,
  floor = MIN_FEE_OLTIN,
): bigint {
  let fee = ceilDiv(requiredEth * rate, ONE);
  fee = ceilDiv(fee * (10_000n + surchargeBps), 10_000n);
  return fee < floor ? floor : fee;
}
