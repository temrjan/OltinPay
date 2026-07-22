import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { checkOperator } from "@/lib/operator";

// UX-only pre-check so the panel can show/hide before the operator acts. The
// real protection is that every bank action route re-checks the password
// server-side (see bankRoute.operatorOk).
export async function POST(req: NextRequest): Promise<NextResponse> {
  const body = (await req.json().catch(() => ({}))) as { password?: string };
  if (!checkOperator(body.password)) {
    return NextResponse.json(
      { error: "Invalid operator password" },
      { status: 401 },
    );
  }
  return NextResponse.json({ ok: true });
}
