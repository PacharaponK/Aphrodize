import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const COOKIE = "aphrodize_daily_health";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function currentUser(request: NextRequest): string | null {
  const parts = request.cookies.get(COOKIE)?.value.split(".");
  if (!parts || parts.length !== 3) return null;
  const [id, expiry, mac] = parts;
  if (!UUID.test(id) || !/^\d{13}$/.test(expiry) || !/^[0-9a-f]{64}$/.test(mac)) return null;
  if (Date.now() >= Number(expiry)) return null;

  const secret = process.env.ANALYSIS_SESSION_SECRET;
  if (!secret) return null;
  const expected = Buffer.from(createHmac("sha256", secret).update(id + "." + expiry).digest("hex"), "hex");
  const supplied = Buffer.from(mac, "hex");
  return supplied.length === expected.length && timingSafeEqual(supplied, expected) ? id : null;
}

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

function apiHeaders(): HeadersInit {
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  if (!username || !password) throw new Error("Backend credentials are not configured");
  return { Authorization: "Basic " + Buffer.from(username + ":" + password).toString("base64") };
}

function backendUrl(path: string): string {
  const base = (process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  return base + "/api/v1" + path;
}

async function backendFailure(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Daily health profile request failed";
  return failed(response.status, detail);
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const userId = currentUser(request);
  if (!userId) {
    return NextResponse.json(
      {
        has_session: false,
        consent_active: false,
        age_guidance_consent_active: false,
        can_report_outcomes: false,
        age_band: null,
        smoking_status: null,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const response = await fetch(backendUrl("/daily-health/users/" + userId + "/profile"), {
      headers: apiHeaders(),
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    const profile = await response.json();
    return NextResponse.json({ has_session: true, ...profile }, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return failed(503, "Could not load personal health settings");
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== request.nextUrl.protocol + "//" + host)) {
    return failed(403, "Invalid request origin");
  }

  const userId = currentUser(request);
  if (!userId) return new NextResponse(null, { status: 204 });

  try {
    const response = await fetch(backendUrl("/daily-health/users/" + userId + "/profile"), {
      method: "DELETE",
      headers: apiHeaders(),
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    return new NextResponse(null, { status: 204 });
  } catch {
    return failed(503, "Could not delete personal health settings");
  }
}
