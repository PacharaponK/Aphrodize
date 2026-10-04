import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

const MAX_BODY_BYTES = 16_384;

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
    target_date?: string | null;
    forecast_receipt?: string | null;
  } | null;
  personalization_consent?: boolean;
  age_guidance_consent?: boolean;
  model_training_consent?: boolean;
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
  if (!Number.isInteger(value.sleep_duration_minutes) || Number(value.sleep_duration_minutes) < 0 || Number(value.sleep_duration_minutes) > 600) return false;
  if (!Number.isInteger(value.water_intake_ml) || Number(value.water_intake_ml) < 0 || Number(value.water_intake_ml) > 20_000) return false;
  if (!Number.isInteger(value.outdoor_exposure_choice) || Number(value.outdoor_exposure_choice) < 1 || Number(value.outdoor_exposure_choice) > 4) return false;
  if (value.timezone !== undefined && (typeof value.timezone !== "string" || value.timezone.length > 64)) return false;
  if (value.personalization_consent !== undefined && typeof value.personalization_consent !== "boolean") return false;
  if (value.age_guidance_consent !== undefined && typeof value.age_guidance_consent !== "boolean") return false;
  if (value.model_training_consent !== undefined && typeof value.model_training_consent !== "boolean") return false;
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
  const receipt = value.prediction.forecast_receipt;
  if (receipt != null && (typeof receipt !== "string" || receipt.length > 8192)) return false;
  const targetDate = value.prediction.target_date;
  if (targetDate !== undefined && targetDate !== null) {
    const parsedTarget = typeof targetDate === "string" && /^\d{4}-\d{2}-\d{2}$/.test(targetDate)
      ? new Date(`${targetDate}T00:00:00.000Z`)
      : null;
    const targetIsValid = parsedTarget !== null
      && !Number.isNaN(parsedTarget.valueOf())
      && parsedTarget.toISOString().slice(0, 10) === targetDate;
    const nextDate = new Date(`${date}T00:00:00.000Z`);
    nextDate.setUTCDate(nextDate.getUTCDate() + 1);
    if (!targetIsValid || (targetDate !== date && targetDate !== nextDate.toISOString().slice(0, 10))) return false;
  }
  return validScore(value.prediction.thirst_score_0_10)
    && validScore(value.prediction.dryness_score_0_10)
    && (status === "predicted" || status === "not_available" || status === "prediction_failed")
    && (value.prediction.model_id === null
      || (typeof value.prediction.model_id === "string" && value.prediction.model_id.length <= 128));
}

async function backendFailure(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Daily health database request failed";
  return failed(response.status, detail);
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const requestedLimit = Number(request.nextUrl.searchParams.get("limit") ?? 30);
  const limit = Number.isInteger(requestedLimit)
    ? Math.min(90, Math.max(1, requestedLimit))
    : 30;
  const query = new URLSearchParams({ limit: String(limit) });
  for (const field of ["from_date", "to_date"] as const) {
    const value = request.nextUrl.searchParams.get(field);
    if (value !== null) query.set(field, value);
  }

  try {
    const account = await accountSession(request);
    if (!account) {
      return NextResponse.json({ items: [] }, { headers: { "Cache-Control": "no-store" } });
    }
    const response = await fetch(
      backendUrl(`/daily-health/users/${account.userId}/entries?${query.toString()}`),
      { headers: { Authorization: `Bearer ${account.token}` }, cache: "no-store" },
    );
    if (!response.ok) return backendFailure(response);
    return NextResponse.json(await response.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return failed(503, "Could not load daily health history");
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) {
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

  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "กรุณาเข้าสู่ระบบก่อนบันทึกข้อมูลสุขภาพรายวัน");
    const consent = await fetch(backendUrl("/auth/daily-health-consent"), {
      method: "PUT",
      headers: { Authorization: `Bearer ${account.token}` },
      cache: "no-store",
    });
    if (!consent.ok) return backendFailure(consent);
    const saved = await fetch(backendUrl(`/daily-health/users/${account.userId}/entries`), {
      method: "PUT",
      headers: { Authorization: `Bearer ${account.token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        local_date: body.local_date,
        timezone: body.timezone ?? "Asia/Bangkok",
        sleep_duration_minutes: body.sleep_duration_minutes,
        water_intake_ml: body.water_intake_ml,
        outdoor_exposure_choice: body.outdoor_exposure_choice,
        prediction: body.prediction,
        personalization_consent: body.personalization_consent === true,
        age_guidance_consent: body.age_guidance_consent === true,
        model_training_consent: body.model_training_consent === true,
        age_band: body.age_guidance_consent === true ? body.age_band ?? null : null,
        smoking_status: body.personalization_consent === true ? body.smoking_status ?? null : null,
        currently_menstruating: body.personalization_consent === true
          ? body.currently_menstruating ?? null
          : null,
      }),
      cache: "no-store",
    });
    if (!saved.ok) return backendFailure(saved);
    return NextResponse.json(await saved.json(), {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return failed(502, "Could not save daily health data. Check that the backend and database are running.");
  }
}
