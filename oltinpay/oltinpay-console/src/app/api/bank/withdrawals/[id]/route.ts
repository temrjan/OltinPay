import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { bankForward } from "@/lib/bankForward";
import { forwarded, operatorOk, unauthorized } from "@/lib/bankRoute";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Confirm (burn) or reject a pending withdrawal. Server-signed. The id is
// validated as a UUID before it is interpolated into the upstream path, so a
// crafted id cannot redirect the signed request to another endpoint.
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  if (!operatorOk(req)) return unauthorized();
  const { id } = await params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json(
      { error: "invalid withdrawal id" },
      { status: 400 },
    );
  }
  const { action } = (await req.json().catch(() => ({}))) as {
    action?: string;
  };
  if (action !== "confirm" && action !== "reject") {
    return NextResponse.json(
      { error: "action must be 'confirm' or 'reject'" },
      { status: 400 },
    );
  }
  return forwarded(
    await bankForward(`/bank/withdrawals/${id}/${action}`, "POST"),
  );
}
