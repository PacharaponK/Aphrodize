import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const COOKIE = "aphrodize_daily_health";
const YEAR_MS = 365 * 24 * 60 * 60 * 1000;
const MAX_BODY_BYTES = 16_384;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type DailyHealthRequest = {
  consent_to_store: true;
  local_date: string;
  timezone?: string;
  sleep_duration_minutes: number;
  water_intake_ml: number;
  outdoor_exposure_choice: number;
  prediction: {
    thirst_score_0_10: number | null;
    dryness_score_0_10: number | null;
    prediction_status: "predicted" | "not_available" | "prediction_failed";
    model_id: string | null;
  } | null;
  personalization_consent?: boolean;
  age_guidance_consent?: boolean;
  age_band?: "13_17" | "18_60" | "61_64" | "65_plus" | null;
  smoking_status?: "current" | "former" | "never" | "prefer_not_to_say" | null;
  currently_menstruating?: boolean | null;
};

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validScore(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 10);
}

function isDailyHealthRequest(value: unknown): value is DailyHealthRequest {
  if (!isRecord(value) || value.consent_to_store !== true) return false;
  const date = value.local_date;
  const parsedDate = typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date)
    ? new Date(`${date}T00:00:00.000Z`)
    : null;
  const dateIsValid = parsedDate !== null && !Number.isNaN(parsedDate.valueOf())
    && parsedDate.toISOString().slice(0, 10) === date;
  if (!dateIsValid) return false;
  if (!Number.isInteger(value.sleep_duration_minutes) || Number(value.sleep_duration_minutes) < 0 || Number(value.sleep_duration_minutes) > 540) return false;
  if (!Number.isInteger(value.water_intake_ml) || Number(value.water_intake_ml) < 0 || Number(value.water_intake_ml) > 20_000) return false;
  if (!Number.isInteger(value.outdoor_exposure_choice) || Number(value.outdoor_exposure_choice) < 1 || Number(value.outdoor_exposure_choice) > 4) return false;
  if (value.timezone !== undefined && (typeof value.timezone !== "string" || value.timezone.length > 64)) return false;
  if (value.personalization_consent !== undefined && typeof value.personalization_consent !== "boolean") return false;
  if (value.age_guidance_consent !== undefined && typeof value.age_guidance_consent !== "boolean") return false;
  if (value.age_band !== undefined
    && value.age_band !== null
    && !["13_17", "18_60", "61_64", "65_plus"].includes(String(value.age_band))) return false;
  if (value.smoking_status !== undefined
    && value.smoking_status !== null
    && !["current", "former", "never", "prefer_not_to_say"].includes(String(value.smoking_status))) return false;
  if (value.currently_menstruating !== undefined
    && value.currently_menstruating !== null
    && typeof value.currently_menstruating !== "boolean") return false;
  if (value.personalization_consent !== true
    && (value.smoking_status != null || value.currently_menstruating != null)) return false;
  if (value.age_guidance_consent !== true && value.age_band != null) return false;
  if (value.prediction === null) return true;
  if (!isRecord(value.prediction)) return false;
  const status = value.prediction.prediction_status;
  return validScore(value.prediction.thirst_score_0_10)
    && validScore(value.prediction.dryness_score_0_10)
    && (status === "predicted" || status === "not_available" || status === "prediction_failed")
    && (value.prediction.model_id === null
      || (typeof value.prediction.model_id === "string" && value.prediction.model_id.length <= 128));
}

function apiHeaders(): HeadersInit {
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  if (!username || !password) throw new Error("Backend credentials are not configured");
  return { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` };
}

function backendUrl(path: string): string {
  return `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1${path}`;
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
  const detail = typeof body?.detail === "string" ? body.detail : "Daily health database request failed";
  return failed(response.status, detail);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) {
    return failed(403, "Invalid request origin");
  }
  if (Number(request.headers.get("content-length")) > MAX_BODY_BYTES) {
    return failed(413, "Request body is too large");
  }

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
  if (!isDailyHealthRequest(body)) {
    return failed(400, "Valid daily health data and storage consent are required");
  }

  let userId = currentUser(request);
  let cookieExpiry: number | null = null;
  try {
    const headers = apiHeaders();
    if (!userId) {
      const consent = await fetch(backendUrl("/consents"), {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ version: "daily-health-v1" }),
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

    const saved = await fetch(backendUrl(`/daily-health/users/${userId}/entries`), {
      method: "PUT",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({
        local_date: body.local_date,
        timezone: body.timezone ?? "Asia/Bangkok",
        sleep_duration_minutes: body.sleep_duration_minutes,
        water_intake_ml: body.water_intake_ml,
        outdoor_exposure_choice: body.outdoor_exposure_choice,
        prediction: body.prediction,
        personalization_consent: body.personalization_consent === true,
        age_guidance_consent: body.age_guidance_consent === true,
        age_band: body.age_guidance_consent === true ? body.age_band ?? null : null,
        smoking_status: body.personalization_consent === true ? body.smoking_status ?? null : null,
        currently_menstruating: body.personalization_consent === true
          ? body.currently_menstruating ?? null
          : null,
      }),
      cache: "no-store",
    });
    if (!saved.ok) {
      const response = await backendFailure(saved);
      if (cookieExpiry) setUserCookie(response, userId, cookieExpiry);
      return response;
    }
    const response = NextResponse.json(await saved.json(), {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
    if (cookieExpiry) setUserCookie(response, userId, cookieExpiry);
    return response;
  } catch {
    const response = failed(502, "Could not save daily health data. Check that the backend and database are running.");
    if (cookieExpiry && userId) setUserCookie(response, userId, cookieExpiry);
    return response;
  }
}
