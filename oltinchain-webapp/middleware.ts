import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  // Telegram Mini App - no auth routes needed
  // TelegramAuthProvider handles authentication
  return NextResponse.next()
}

export const config = {
  matcher: [],
}
