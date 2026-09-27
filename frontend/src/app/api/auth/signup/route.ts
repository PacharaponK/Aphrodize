import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SESSION_COOKIE = "aphrodize_session";
const WEEK_SECONDS = 7 * 24 * 60 * 60;

function backendUrl(): string {
  return `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/auth/signup`;
}

function messageFrom(detail: unknown): string {
  if (typeof detail === "string") return detail;
  return "สร้างบัญชีไม่สำเร็จ โปรดลองอีกครั้ง";
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
  }

  try {
    const response = await fetch(backendUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return NextResponse.json(
        { detail: messageFrom(body?.detail) },
        { status: response.status, headers: { "Cache-Control": "no-store" } },
      );
    }
    if (typeof body?.access_token !== "string") {
      return NextResponse.json(
        { detail: "บริการสร้างบัญชีส่งข้อมูลไม่ครบ" },
        { status: 502, headers: { "Cache-Control": "no-store" } },
      );
    }
    const { access_token: token, ...account } = body;
    const result = NextResponse.json(account, {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
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
      { detail: "ยังเชื่อมต่อบริการสร้างบัญชีไม่ได้ กรุณาลองใหม่อีกครั้ง" },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
