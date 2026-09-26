import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const COOKIE = "aphrodize_daily_health";
const MAX_BODY_BYTES = 16_384;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type OutcomeInput = {
  consent_to_store: true;
  target_date: string;
  reported_energy_level_0_10: number | null;
  reported_thirst_level_0_10: number | null;
};

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

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

function validScore(value: unknown): value is number | null {
  return value === null
    || (typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 10);
}

function isOutcomeInput(value: unknown): value is OutcomeInput {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const body = value as Record<string, unknown>;
  const date = body.target_date;
  const parsedDate = typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date)
    ? new Date(date + "T00:00:00.000Z")
    : null;
  const validDate = parsedDate !== null
    && !Number.isNaN(parsedDate.valueOf())
    && parsedDate.toISOString().slice(0, 10) === date;
  return body.consent_to_store === true
    && validDate
    && validScore(body.reported_energy_level_0_10)
    && validScore(body.reported_thirst_level_0_10)
    && (body.reported_energy_level_0_10 !== null || body.reported_thirst_level_0_10 !== null);
}

async function backendFailure(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Could not save reported outcome";
  return failed(response.status, detail);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== request.nextUrl.protocol + "//" + host)) {
    return failed(403, "Invalid request origin");
  }

  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BODY_BYTES) return failed(413, "Request body is too large");

  let body: unknown;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
      return failed(413, "Request body is too large");
    }
    body = JSON.parse(raw);
  } catch {
    return failed(400, "Expected a JSON request body");
  }
  if (!isOutcomeInput(body)) return failed(400, "Valid self-reported outcome and consent are required");

  const userId = currentUser(request);
  if (!userId) return failed(401, "Save a daily health entry before reporting an outcome");

  try {
    const saved = await fetch(backendUrl("/daily-health/users/" + userId + "/outcomes"), {
      method: "PUT",
      headers: { ...apiHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        target_date: body.target_date,
        reported_energy_level_0_10: body.reported_energy_level_0_10,
        reported_thirst_level_0_10: body.reported_thirst_level_0_10,
      }),
      cache: "no-store",
    });
    if (!saved.ok) return backendFailure(saved);
    return NextResponse.json(await saved.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return failed(503, "Could not save the reported outcome. Check that the backend is running.");
  }
}
