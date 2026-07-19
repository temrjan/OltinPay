import type { NextRequest } from "next/server";

import { bankForward } from "@/lib/bankForward";
import { forwarded, operatorOk, unauthorized } from "@/lib/bankRoute";

// List pending withdrawals for the operator queue. Server-signed GET.
export async function GET(req: NextRequest) {
  if (!operatorOk(req)) return unauthorized();
  return forwarded(
    await bankForward("/bank/withdrawals?status=pending", "GET"),
  );
}
