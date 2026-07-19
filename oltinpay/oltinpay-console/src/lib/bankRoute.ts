import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import type { BankResult } from "./bankForward";
import { checkOperator } from "./operator";

// Server-side operator gate applied by every bank action route (E3). The panel
// sends the password in X-Operator-Password and it is re-checked on EVERY
// request, so the gate cannot be bypassed from the client.
export const operatorOk = (req: NextRequest): boolean =>
  checkOperator(req.headers.get("x-operator-password"));

export const unauthorized = (): NextResponse =>
  NextResponse.json({ error: "Invalid operator password" }, { status: 401 });

// Relay the upstream API result (tx hash / status / error) to the authenticated
// operator with the upstream status code preserved.
export const forwarded = (r: BankResult): NextResponse =>
  NextResponse.json(r.body, { status: r.status });
