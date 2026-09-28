import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SESSION_COOKIE = "aphrodize_session";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "กรุณาเข้าสู่ระบบก่อน" }, { status: 401 });
  }
  try {
    const response = await fetch(`${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const body = await response.json().catch(() => null);
    return NextResponse.json(body, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "ยังเชื่อมต่อข้อมูลโปรไฟล์ไม่ได้" }, { status: 502 });
  }
}
