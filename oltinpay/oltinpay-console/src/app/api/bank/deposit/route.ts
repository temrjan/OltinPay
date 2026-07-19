import type { NextRequest } from "next/server";

import { bankForward } from "@/lib/bankForward";
import { forwarded, operatorOk, unauthorized } from "@/lib/bankRoute";

// Confirm a fiat deposit -> mint UZD (userId|oltinId + amountUzs + bankTxId).
// Server-signed; idempotent on bankTxId at the API.
export async function POST(req: NextRequest) {
  if (!operatorOk(req)) return unauthorized();
  const payload = await req.json().catch(() => ({}));
  return forwarded(await bankForward("/bank/deposits", "POST", payload));
}
