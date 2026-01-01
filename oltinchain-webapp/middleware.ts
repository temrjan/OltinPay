import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Routes that require authentication
const protectedRoutes = ["/dashboard", "/buy", "/sell", "/wallet", "/transfer"]

// Routes that should redirect to dashboard if authenticated
const authRoutes = ["/auth/login", "/auth/register"]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check for access token in cookies (set by client after login)
  // Note: For Telegram Mini App, auth is typically handled client-side
  // This middleware provides an additional layer of protection
  const token = request.cookies.get("access_token")?.value

  // Check if route is protected
  const isProtectedRoute = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  )

  // Check if route is auth route
  const isAuthRoute = authRoutes.some((route) => pathname.startsWith(route))

  // Redirect to login if accessing protected route without token
  if (isProtectedRoute && !token) {
    const loginUrl = new URL("/auth/login", request.url)
    loginUrl.searchParams.set("redirect", pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Redirect to dashboard if accessing auth route with token
  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/buy/:path*",
    "/sell/:path*",
    "/wallet/:path*",
    "/transfer/:path*",
    "/auth/:path*",
  ],
}
