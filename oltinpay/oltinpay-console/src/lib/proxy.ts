import { NextResponse } from "next/server";

// Wrap a server-side upstream fetch as a same-origin JSON route so the browser
// polls the Console (no CORS on the API; API_URL stays server-side). On upstream
// failure returns 502 with a message the client can surface instead of throwing.
export async function proxyJson<T>(fn: () => Promise<T>): Promise<NextResponse> {
  try {
    return NextResponse.json(await fn());
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "upstream error" },
      { status: 502 },
    );
  }
}
