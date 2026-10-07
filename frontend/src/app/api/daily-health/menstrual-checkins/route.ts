import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const requestedLimit = Number(request.nextUrl.searchParams.get("limit") ?? 28);
  const limit = Number.isInteger(requestedLimit) ? Math.min(90, Math.max(1, requestedLimit)) : 28;
  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "กรุณาเข้าสู่ระบบก่อนดูข้อมูลรอบเดือน");
    const response = await fetch(
      backendUrl(`/daily-health/users/${account.userId}/menstrual-checkins?limit=${limit}`),
      { headers: { Authorization: `Bearer ${account.token}` }, cache: "no-store" },
    );
    const body = await response.json().catch(() => null);
    if (response.status === 403) {
      return NextResponse.json({ items: [], consent_required: true }, { headers: { "Cache-Control": "no-store" } });
    }
    if (!response.ok) return failed(response.status, typeof body?.detail === "string" ? body.detail : "โหลดข้อมูลรอบเดือนไม่สำเร็จ");
    return NextResponse.json({ items: body }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return failed(503, "ยังเชื่อมต่อบริการข้อมูลรอบเดือนไม่ได้");
  }
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) return failed(403, "Invalid request origin");
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return failed(400, "Expected a JSON request body");
  }
  if (typeof body !== "object" || body === null || Array.isArray(body)) return failed(400, "Invalid menstrual check-in");
  const input = body as Record<string, unknown>;
  if (typeof input.local_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(input.local_date)
    || typeof input.currently_menstruating !== "boolean") return failed(400, "Invalid menstrual check-in");
  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "กรุณาเข้าสู่ระบบก่อนบันทึกข้อมูลรอบเดือน");
    const response = await fetch(backendUrl(`/daily-health/users/${account.userId}/menstrual-checkins`), {
      method: "PUT",
      headers: { Authorization: `Bearer ${account.token}`, "Content-Type": "application/json" },
      body: JSON.stringify(input),
      cache: "no-store",
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) return failed(response.status, typeof result?.detail === "string" ? result.detail : "บันทึกข้อมูลรอบเดือนไม่สำเร็จ");
    return NextResponse.json(result, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return failed(503, "ยังเชื่อมต่อบริการข้อมูลรอบเดือนไม่ได้");
  }
}
