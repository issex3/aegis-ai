import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPrefixes = ["/dashboard", "/agents", "/assessments", "/sandboxes", "/findings", "/remediation", "/intelligence", "/reports", "/onboarding", "/settings", "/programmes", "/library"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const needsSession = protectedPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  if (needsSession && !request.cookies.get("aegis_session")) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
