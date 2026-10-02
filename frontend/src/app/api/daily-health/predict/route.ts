import type { NextRequest } from "next/server";
import { accountSession, backendUrl } from "@/lib/daily-health-session";
import { forwardDailyHealthPrediction } from "@/lib/daily-health-prediction";

const MAX_BODY_BYTES = 16_384;

function failure(status: number, detail: string): Response {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function addConsentedProfileContext(request: NextRequest, body: string): Promise<string> {
  let payload: unknown;
  try {
    payload = JSON.parse(body);
  } catch {
    return body;
  }
  if (!isRecord(payload)) return body;

  const enrichedPayload: Record<string, unknown> = { ...payload, weight_kg: null };
  const account = await accountSession(request);
  if (!account) return JSON.stringify(enrichedPayload);

  const profileResponse = await fetch(
    backendUrl(`/daily-health/users/${account.userId}/profile`),
    { headers: { Authorization: `Bearer ${account.token}` }, cache: "no-store" },
  );
  if (!profileResponse.ok) throw new Error("Could not load the consented profile");

  const profile: unknown = await profileResponse.json();
  if (!isRecord(profile)) throw new Error("Backend returned an invalid profile");

  if (profile.weight_profile_consent_active === true
    && typeof profile.weight_kg === "number"
    && Number.isFinite(profile.weight_kg)
    && profile.weight_kg >= 1
    && profile.weight_kg <= 500) {
    enrichedPayload.weight_kg = profile.weight_kg;
  }

  const ageBand = profile.age_band;
  if (profile.age_guidance_consent_active === true
    && ["13_17", "18_60", "61_64", "65_plus"].includes(String(ageBand))) {
    const personalContext = isRecord(payload.personal_context) ? payload.personal_context : {};
    enrichedPayload.personal_context = {
      ...personalContext,
      age_guidance_consent_given: true,
      age_band: ageBand,
    };
  }

  return JSON.stringify(enrichedPayload);
}

export async function POST(request: NextRequest): Promise<Response> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin) {
    const originUrl = new URL(origin);
    const requestUrl = new URL(request.url);
    const forwardedHost = request.headers.get("x-forwarded-host");
    const allowedHosts = new Set([host, forwardedHost, requestUrl.host].filter(Boolean));
    const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",")[0];
    const expectedProtocol = forwardedProtocol
      ? `${forwardedProtocol.trim()}:`
      : requestUrl.protocol;
    if (!allowedHosts.has(originUrl.host) || originUrl.protocol !== expectedProtocol) {
      return failure(403, "Invalid request origin");
    }
  }
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BODY_BYTES) return failure(413, "Request body is too large");

  let body: string;
  try {
    body = await request.text();
  } catch {
    return failure(400, "Expected a JSON request body");
  }
  if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES) {
    return failure(413, "Request body is too large");
  }

  let enrichedBody: string;
  try {
    enrichedBody = await addConsentedProfileContext(request, body);
  } catch {
    return failure(503, "Could not load your consented profile details for this score.");
  }

  const upstream = await forwardDailyHealthPrediction(enrichedBody);
  return Response.json(upstream.payload, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}
