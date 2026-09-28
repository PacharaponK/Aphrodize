import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const COOKIE = "aphrodize_analysis";
const ANONYMOUS_COOKIE = "aphrodize_anonymous";
const DAY_MS = 24 * 60 * 60 * 1000;
const REVIEW_MS = 30 * DAY_MS;
const MAX_BYTES = 10 * 1024 * 1024;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function apiHeaders(): HeadersInit {
  // Read service credentials only on the server; never send them to the browser.
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  if (!username || !password) throw new Error("Backend credentials are not configured");
  return { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` };
}

function backendUrl(path: string): string {
  // Every proxied endpoint lives under the backend's /api/v1 prefix.
  return `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1${path}`;
}

function signature(value: string): string {
  // HMAC prevents clients from changing analysis or review-user IDs in cookies.
  const secret = process.env.ANALYSIS_SESSION_SECRET;
  if (!secret) throw new Error("Analysis session secret is not configured");
  return createHmac("sha256", secret).update(value).digest("hex");
}

function currentAnalysis(request: NextRequest): string | null {
  // Read the latest analysis ID, expiry, and HMAC from the browser cookie.
  const parts = request.cookies.get(COOKIE)?.value.split(".");
  if (!parts || parts.length !== 3) return null;
  const [id, expiry, mac] = parts;
  if (!UUID.test(id) || !/^\d{13}$/.test(expiry) || !/^[0-9a-f]{64}$/.test(mac)) return null;
  if (Date.now() >= Number(expiry)) return null;
  // Compare signatures in constant time before accepting the stored ID.
  const expected = signature(`${id}.${expiry}`);
  return timingSafeEqual(Buffer.from(mac, "hex"), Buffer.from(expected, "hex")) ? id : null;
}

function anonymousSession(request: NextRequest): { userId: string; token: string } | null {
  const value = request.cookies.get(ANONYMOUS_COOKIE)?.value;
  if (!value) return null;
  const separator = value.indexOf(":");
  const userId = value.slice(0, separator);
  const token = value.slice(separator + 1);
  return separator > 0 && UUID.test(userId) && /^[\w.-]+$/.test(token)
    ? { userId, token }
    : null;
}

function failed(status: number, message: string): NextResponse {
  return NextResponse.json({ detail: message }, { status, headers: { "Cache-Control": "no-store" } });
}

async function backendError(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Backend request failed";
  return failed(response.status, detail);
}

// Keep backend credentials on the server while creating consents and queuing analysis.
export async function POST(request: NextRequest): Promise<NextResponse> {
  // Reject cross-origin form posts before accepting private image bytes.
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) {
    return failed(403, "Invalid request origin");
  }
  // Limit the request envelope and then validate the parsed image itself.
  if (Number(request.headers.get("content-length")) > MAX_BYTES + 100_000) {
    return failed(413, "Image exceeds 10 MiB");
  }
  const form = await request.formData();
  const image = form.get("image");
  const wantsAnnotation = form.get("annotation_consent") === "yes";
  // The analysis consent is mandatory; review consent is a separate choice.
  if (form.get("consent") !== "yes") return failed(403, "Consent is required");
  if (!(image instanceof File) || !IMAGE_TYPES.has(image.type) || !image.size) {
    return failed(415, "Choose a JPEG, PNG, or WebP image");
  }
  if (image.size > MAX_BYTES) return failed(413, "Image exceeds 10 MiB");

  try {
    let anonymous = anonymousSession(request);
    if (!anonymous) {
      const consent = await fetch(backendUrl("/consents"), {
        method: "POST",
        headers: { ...apiHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ version: "1.0" }),
        cache: "no-store",
      });
      if (!consent.ok) return backendError(consent);
      const { user_id, access_token } = await consent.json();
      if (typeof user_id !== "string" || !UUID.test(user_id) || typeof access_token !== "string") {
        throw new Error("Invalid anonymous session");
      }
      anonymous = { userId: user_id, token: access_token };
    }
    const { userId, token } = anonymous;
    if (wantsAnnotation) {
      // Grant the separate human-review consent before queuing the image.
      const reviewConsent = await fetch(backendUrl(`/consents/users/${userId}/annotations`), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (!reviewConsent.ok) return backendError(reviewConsent);
    }
    // Forward only the image to the protected analysis endpoint.
    const upload = new FormData();
    upload.set("image", image);
    const analysis = await fetch(backendUrl(`/analyses/users/${userId}`), {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: upload,
      cache: "no-store",
    });
    if (!analysis.ok) return backendError(analysis);
    const data = await analysis.json();
    if (typeof data.id !== "string" || !UUID.test(data.id)) throw new Error("Invalid analysis id");
    // Return the queued/rejected row immediately; inference continues in Redis.
    const response = NextResponse.json(data, { status: 202, headers: { "Cache-Control": "no-store" } });
    if (!anonymousSession(request)) {
      response.cookies.set(ANONYMOUS_COOKIE, `${userId}:${token}`, {
        httpOnly: true,
        sameSite: "strict",
        secure: process.env.NODE_ENV === "production",
        path: "/api/analysis",
        maxAge: REVIEW_MS / 1000,
      });
    }
    const expiry = Date.now() + DAY_MS;
    // ponytail: one browser session tracks its latest analysis; account history needs real user auth.
    response.cookies.set(COOKIE, `${data.id}.${expiry}.${signature(`${data.id}.${expiry}`)}`, {
      httpOnly: true,
      sameSite: "strict",
      secure: process.env.NODE_ENV === "production",
      path: "/api/analysis",
      maxAge: DAY_MS / 1000,
    });
    return response;
  } catch {
    return failed(502, "Could not reach the analysis service");
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  // Apply the same origin check used by POST before revoking consent.
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) {
    return failed(403, "Invalid request origin");
  }
  try {
    const anonymous = anonymousSession(request);
    if (!anonymous) return failed(401, "No active analysis session in this browser");
    const response = await fetch(backendUrl(`/consents/users/${anonymous.userId}/annotations`), {
      method: "DELETE",
      headers: { Authorization: `Bearer ${anonymous.token}` },
      cache: "no-store",
    });
    if (!response.ok) return backendError(response);
    return new NextResponse(null, { status: 204 });
  } catch {
    return failed(502, "Could not revoke annotation consent");
  }
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    // A valid signed cookie authorizes reading this browser's latest analysis.
    const id = currentAnalysis(request);
    if (!id) return failed(401, "No active analysis in this browser");
    const anonymous = anonymousSession(request);
    if (!anonymous) return failed(401, "No active analysis session in this browser");
    const artifact = request.nextUrl.searchParams.get("artifact");
    // Only the two display images can be fetched through this proxy.
    if (artifact && artifact !== "mask" && artifact !== "overlay") {
      return failed(400, "Unknown artifact");
    }
    const path = artifact
      ? `/analyses/${id}/artifacts/${artifact}`
      : `/analyses/${id}`;
    const response = await fetch(backendUrl(path), {
      headers: { Authorization: `Bearer ${anonymous.token}` },
      cache: "no-store",
    });
    if (!response.ok) return backendError(response);
    if (artifact) {
      // Stream image bytes with private, non-cacheable response headers.
      return new NextResponse(await response.arrayBuffer(), {
        headers: { "Content-Type": "image/png", "Cache-Control": "private, no-store" },
      });
    }
    return NextResponse.json(await response.json(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return failed(502, "Could not reach the analysis service");
  }
}
