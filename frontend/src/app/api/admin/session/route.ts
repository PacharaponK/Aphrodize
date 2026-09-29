import { NextRequest, NextResponse } from "next/server";
import { ADMIN_COOKIE, ADMIN_SECONDS, adminConfigured, adminSessionValue, hasAdminSession, sameOrigin, validAdminCredentials } from "@/lib/admin-auth";

export const runtime = "nodejs";

export function GET(request: NextRequest) {
  return NextResponse.json(
    { configured: adminConfigured(), authenticated: hasAdminSession(request) },
    { headers: { "Cache-Control": "no-store" } },
  );
}

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  if (!adminConfigured()) return NextResponse.json({ detail: "Admin access is not configured" }, { status: 503 });
  if (Number(request.headers.get("content-length")) > 4096) {
    return NextResponse.json({ detail: "Request too large" }, { status: 413 });
  }
  const body = await request.json().catch(() => null);
  if (typeof body?.username !== "string" || typeof body?.password !== "string" ||
      !validAdminCredentials(body.username, body.password)) {
    return NextResponse.json({ detail: "ชื่อผู้ใช้หรือรหัสผ่านแอดมินไม่ถูกต้อง" }, { status: 401 });
  }
  const response = NextResponse.json({ authenticated: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(ADMIN_COOKIE, adminSessionValue(), {
    httpOnly: true, sameSite: "strict", secure: process.env.NODE_ENV === "production",
    path: "/", maxAge: ADMIN_SECONDS,
  });
  return response;
}

export function DELETE(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  const response = NextResponse.json({ authenticated: false }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.delete(ADMIN_COOKIE);
  return response;
}
