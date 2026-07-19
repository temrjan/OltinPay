import { timingSafeEqual } from "node:crypto";

// Server-only operator gate (E3, demo). The bank action routes re-check this on
// EVERY request, so the gate is server-side and cannot be bypassed from the
// client (a client toggle only decides whether to show the panel). Constant-time
// compare; the length pre-check is required by timingSafeEqual and only leaks
// length (acceptable for a demo testnet operator gate).
export function checkOperator(password: string | null | undefined): boolean {
  const expected = process.env.CONSOLE_OPERATOR_PASSWORD;
  if (!expected || !password) {
    return false;
  }
  const a = Buffer.from(password, "utf-8");
  const b = Buffer.from(expected, "utf-8");
  if (a.length !== b.length) {
    return false;
  }
  return timingSafeEqual(a, b);
}
