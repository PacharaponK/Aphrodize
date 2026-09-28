import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const COOKIE = "aphrodize_daily_health";
const YEAR_MS = 365 * 24 * 60 * 60 * 1000;
const MAX_BODY_BYTES = 2_048;
const WEIGHT_PROFILE_CONSENT_VERSION = "daily-health-weight-profile-v1";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function failure(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function apiHeaders(): HeadersInit {
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  if (!username || !password) throw new Error("Backend credentials are not configured");
  return { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` };
}

function backendUrl(path: string): string {
  const base = (process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  return `${base}/api/v1${path}`;
}

function signature(value: string): string {
  const secret = process.env.ANALYSIS_SESSION_SECRET;
  if (!secret) throw new Error("Session signing secret is not configured");
  return createHmac("sha256", secret).update(value).digest("hex");
}

function currentUser(request: NextRequest): string | null {
  const parts = request.cookies.get(COOKIE)?.value.split(".");
  if (!parts || parts.length !== 3) return null;
  const [id, expiry, mac] = parts;
  if (!UUID.test(id) || !/^\d{13}$/.test(expiry) || !/^[0-9a-f]{64}$/.test(mac)) return null;
  if (Date.now() >= Number(expiry)) return null;
  const expected = Buffer.from(signature(`${id}.${expiry}`), "hex");
  const supplied = Buffer.from(mac, "hex");
  return supplied.length === expected.length && timingSafeEqual(supplied, expected) ? id : null;
}

function setUserCookie(response: NextResponse, userId: string, expiry: number): void {
  response.cookies.set(COOKIE, `${userId}.${expiry}.${signature(`${userId}.${expiry}`)}`, {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/api/daily-health",
    maxAge: Math.floor((expiry - Date.now()) / 1000),
  });
}

async function backendFailure(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Daily health profile request failed";
  return failure(response.status, detail);
}

function hasSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  return !origin || Boolean(host && origin === `${request.nextUrl.protocol}//${host}`);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!hasSameOrigin(request)) return failure(403, "Invalid request origin");
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

  let userId = currentUser(request);
  let cookieExpiry: number | null = null;
  try {
    const headers = apiHeaders();
    if (!userId) {
      const consent = await fetch(backendUrl("/consents"), {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ version: WEIGHT_PROFILE_CONSENT_VERSION }),
        cache: "no-store",
      });
      if (!consent.ok) return backendFailure(consent);
      const result: unknown = await consent.json();
      if (!isRecord(result) || typeof result.user_id !== "string" || !UUID.test(result.user_id)) {
        throw new Error("Backend returned an invalid user identity");
      }
      userId = result.user_id;
      cookieExpiry = Date.now() + YEAR_MS;
    }

    const saved = await fetch(backendUrl(`/daily-health/users/${userId}/profile/weight`), {
      method: "PUT",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ weight_kg: input.weight_kg, consent_given: true }),
      cache: "no-store",
    });
    if (!saved.ok) {
      const response = await backendFailure(saved);
      if (cookieExpiry && userId) setUserCookie(response, userId, cookieExpiry);
      return response;
    }
    const response = NextResponse.json(await saved.json(), {
      headers: { "Cache-Control": "no-store" },
    });
    if (cookieExpiry && userId) setUserCookie(response, userId, cookieExpiry);
    return response;
  } catch {
    const response = failure(503, "Could not save profile weight");
    if (cookieExpiry && userId) setUserCookie(response, userId, cookieExpiry);
    return response;
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  if (!hasSameOrigin(request)) return failure(403, "Invalid request origin");
  const userId = currentUser(request);
  if (!userId) return new NextResponse(null, { status: 204 });

  try {
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
