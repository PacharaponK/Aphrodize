import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) return failed(403, "Invalid request origin");
  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "กรุณาเข้าสู่ระบบก่อนให้ความยินยอม");
    const response = await fetch(
      backendUrl(`/daily-health/users/${account.userId}/menstrual-checkins/consent`),
      { method: "PUT", headers: { Authorization: `Bearer ${account.token}` }, cache: "no-store" },
    );
    const result = await response.json().catch(() => null);
    if (!response.ok) return failed(response.status, typeof result?.detail === "string" ? result.detail : "บันทึกความยินยอมไม่สำเร็จ");
    return NextResponse.json(result, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return failed(503, "ยังเชื่อมต่อบริการข้อมูลรอบเดือนไม่ได้");
  }
}
