import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { accountSession } from "@/lib/daily-health-session";

const PUBLIC_PATHS = new Set([
  "/capture", "/login", "/signup",
  "/api/auth/login", "/api/auth/signup", "/api/auth/logout",
  "/api/analysis", "/api/analysis/recommendations", "/api/health",
  // Admin sign-in and product APIs enforce their own separate admin session.
  "/admin", "/admin/products", "/api/admin/session", "/api/admin/products", "/api/admin/uv", "/api/admin/wrinkle",
]);

export async function proxy(request: NextRequest) {
  const supplied = request.headers.get("x-request-id");
  const id = supplied && /^[0-9a-f]{32}$/i.test(supplied)
    ? supplied.toLowerCase() : randomUUID().replaceAll("-", "");
  const headers = new Headers(request.headers);
  headers.set("x-request-id", id);
  const next = () => {
    const response = NextResponse.next({ request: { headers } });
    response.headers.set("x-request-id", id);
    return response;
  };
  const pathname = request.nextUrl.pathname.replace(/\/$/, "") || "/";
  if (PUBLIC_PATHS.has(pathname)) return next();

  try {
    if (await accountSession(request)) return next();
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
