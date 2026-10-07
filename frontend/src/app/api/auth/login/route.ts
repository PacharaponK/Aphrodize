import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SESSION_COOKIE = "aphrodize_session";
const WEEK_SECONDS = 7 * 24 * 60 * 60;

export async function POST(request: NextRequest): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  }
  try {
    const response = await fetch(`${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(await request.json()),
      cache: "no-store",
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return NextResponse.json(
        { detail: typeof body?.detail === "string" ? body.detail : "เข้าสู่ระบบไม่สำเร็จ" },
        { status: response.status, headers: { "Cache-Control": "no-store" } },
      );
    }
    if (typeof body?.access_token !== "string") throw new Error("Missing access token");
    const { access_token: token, ...account } = body;
    const result = NextResponse.json(account, { headers: { "Cache-Control": "no-store" } });
    result.cookies.set(SESSION_COOKIE, token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: WEEK_SECONDS,
    });
    return result;
  } catch {
    return NextResponse.json(
      { detail: "ยังเชื่อมต่อบริการเข้าสู่ระบบไม่ได้ กรุณาลองใหม่อีกครั้ง" },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
