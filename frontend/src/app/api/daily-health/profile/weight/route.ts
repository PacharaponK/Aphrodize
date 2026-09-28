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
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BODY_BYTES) return failure(413, "Request body is too large");

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
    return failure(400, "A valid weight and explicit profile consent are required");
  }
  const input = body as Record<string, unknown>;
  if (input.consent_given !== true || typeof input.weight_kg !== "number"
    || !Number.isFinite(input.weight_kg) || input.weight_kg < 1 || input.weight_kg > 500) {
    return failure(400, "A valid weight and explicit profile consent are required");
  }

  try {
    const account = await accountSession(request);
    if (!account) return failure(401, "กรุณาเข้าสู่ระบบก่อนบันทึกน้ำหนัก");
    const userId = account.userId;
    const headers = apiHeaders();
    const saved = await fetch(backendUrl(`/daily-health/users/${userId}/profile/weight`), {
      method: "PUT",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ weight_kg: input.weight_kg, consent_given: true }),
      cache: "no-store",
    });
    if (!saved.ok) return backendFailure(saved);
    const response = NextResponse.json(await saved.json(), {
      headers: { "Cache-Control": "no-store" },
    });
    return response;
  } catch {
    const response = failure(503, "Could not save profile weight");
    return response;
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) return failure(403, "Invalid request origin");
  try {
    const account = await accountSession(request);
    if (!account) return failure(401, "กรุณาเข้าสู่ระบบก่อนลบน้ำหนัก");
    const userId = account.userId;
    const response = await fetch(backendUrl(`/daily-health/users/${userId}/profile/weight`), {
      method: "DELETE",
      headers: apiHeaders(),
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    return new NextResponse(null, { status: 204 });
  } catch {
    return failure(503, "Could not delete profile weight");
  }
}
