import { NextRequest, NextResponse } from "next/server";
import { accountSession } from "@/lib/daily-health-session";

const PUBLIC_PATHS = new Set([
  "/capture", "/login", "/signup",
  "/api/auth/login", "/api/auth/signup", "/api/auth/logout",
  "/api/analysis", "/api/analysis/recommendations",
  // Admin sign-in and product APIs enforce their own separate admin session.
  "/admin/products", "/api/admin/session", "/api/admin/products",
]);

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname.replace(/\/$/, "") || "/";
  if (PUBLIC_PATHS.has(pathname)) return NextResponse.next();

  try {
    if (await accountSession(request)) return NextResponse.next();
  } catch {
    return NextResponse.json({ detail: "Could not verify account session" }, {
      status: 503, headers: { "Cache-Control": "no-store" },
    });
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "กรุณาเข้าสู่ระบบก่อนใช้งาน" }, {
      status: 401, headers: { "Cache-Control": "no-store" },
    });
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", pathname + request.nextUrl.search);
  const response = NextResponse.redirect(login);
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static(?:/|$)|_next/image(?:/|$)|assets(?:/|$)|legacy(?:/|$)|favicon\\.ico$).*)"],
};
