import type { NextRequest } from "next/server";

import { bankForward } from "@/lib/bankForward";
import { forwarded, operatorOk, unauthorized } from "@/lib/bankRoute";

// Post a UZS/USD rate to the on-chain feed (uzsPerUsd + source). Server-signed.
export async function POST(req: NextRequest) {
  if (!operatorOk(req)) return unauthorized();
  const payload = await req.json().catch(() => ({}));
  return forwarded(await bankForward("/bank/fx", "POST", payload));
}
