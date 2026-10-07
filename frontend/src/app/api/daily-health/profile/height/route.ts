import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";
import { accountSession, apiHeaders, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

const MAX_BODY_BYTES = 2_048;

function failure(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

async function backendFailure(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Daily health profile request failed";
  return failure(response.status, detail);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) return failure(403, "Invalid request origin");
  if (Number(request.headers.get("content-length") ?? 0) > MAX_BODY_BYTES) {
    return failure(413, "Request body is too large");
  }

  let body: unknown;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
      return failure(413, "Request body is too large");
    }
    body = JSON.parse(raw);
  } catch {
    return failure(400, "Expected a JSON request body");
  }

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return failure(400, "A valid height and explicit profile consent are required");
  }
  const input = body as Record<string, unknown>;
  if (input.consent_given !== true || typeof input.height_cm !== "number"
    || !Number.isFinite(input.height_cm) || input.height_cm < 30 || input.height_cm > 300) {
    return failure(400, "A valid height and explicit profile consent are required");
  }

  try {
    const account = await accountSession(request);
    if (!account) return failure(401, "กรุณาเข้าสู่ระบบก่อนบันทึกส่วนสูง");
    const response = await fetch(backendUrl(`/daily-health/users/${account.userId}/profile/height`), {
      method: "PUT",
      headers: { ...apiHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ height_cm: input.height_cm, consent_given: true }),
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    return NextResponse.json(await response.json(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return failure(503, "Could not save profile height");
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) return failure(403, "Invalid request origin");
  try {
    const account = await accountSession(request);
    if (!account) return failure(401, "กรุณาเข้าสู่ระบบก่อนลบส่วนสูง");
    const response = await fetch(backendUrl(`/daily-health/users/${account.userId}/profile/height`), {
      method: "DELETE",
      headers: apiHeaders(),
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    return new NextResponse(null, { status: 204 });
  } catch {
    return failure(503, "Could not delete profile height");
  }
}
