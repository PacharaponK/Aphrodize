import { backendFetch as fetch } from "@/lib/backend-fetch";
import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const ANALYSIS_COOKIE = "aphrodize_analysis";
const SESSION_COOKIE = "aphrodize_session";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

function currentAnalysis(request: NextRequest): string | null {
  const parts = request.cookies.get(ANALYSIS_COOKIE)?.value.split(".");
  if (!parts || parts.length !== 3) return null;
  const [id, expiry, mac] = parts;
  if (!UUID.test(id) || !/^\d{13}$/.test(expiry) || !/^[0-9a-f]{64}$/.test(mac) || Date.now() >= Number(expiry)) return null;
  const secret = process.env.ANALYSIS_SESSION_SECRET;
  if (!secret) throw new Error("Analysis session secret is not configured");
  const expected = createHmac("sha256", secret).update(`${id}.${expiry}`).digest();
  const supplied = Buffer.from(mac, "hex");
  return supplied.length === expected.length && timingSafeEqual(supplied, expected) ? id : null;
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ guest_profile_required: true }, { headers: { "Cache-Control": "no-store" } });
  try {
    const profileScope = request.nextUrl.searchParams.get("scope") === "profile";
    const analysisId = currentAnalysis(request);
    if (!profileScope && !analysisId) return failed(404, "ยังไม่มีผลวิเคราะห์ในเบราว์เซอร์นี้");
    const market = request.nextUrl.searchParams.get("market") ?? "TH";
    const budget = request.nextUrl.searchParams.get("max_price_satang");
    if (market !== "TH" && market !== "all") return failed(400, "Invalid product market");
    if (budget !== null && (!/^\d+$/.test(budget) || Number(budget) > 100_000_000)) return failed(400, "Invalid product budget");
    const query = new URLSearchParams({ market });
    if (budget !== null) query.set("max_price_satang", budget);
    const response = await fetch(
      `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/analyses/${profileScope ? "" : `${analysisId}/`}recommendations?${query}`,
      { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" },
    );
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return failed(response.status, typeof body?.detail === "string" ? body.detail : "โหลดคำแนะนำไม่สำเร็จ");
    }
    return NextResponse.json(body, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return failed(502, "ยังเชื่อมต่อบริการคำแนะนำไม่ได้");
  }
}


export async function POST(request: NextRequest): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) return failed(403, "Invalid request origin");
  if (Number(request.headers.get("content-length")) > 4096) return failed(413, "Profile is too large");
  try {
    const text = await request.text();
    if (Buffer.byteLength(text) > 4096) return failed(413, "Profile is too large");
    let answers: unknown;
    try { answers = JSON.parse(text); } catch { return failed(400, "Invalid skin profile"); }
    const market = request.nextUrl.searchParams.get("market") ?? "TH";
    const budget = request.nextUrl.searchParams.get("max_price_satang");
    if (market !== "TH" && market !== "all") return failed(400, "Invalid product market");
    if (budget !== null && (!/^\d+$/.test(budget) || Number(budget) > 100_000_000)) return failed(400, "Invalid product budget");
    const query = new URLSearchParams({ market });
    if (budget !== null) query.set("max_price_satang", budget);
    const analysisId = request.nextUrl.searchParams.get("scope") === "analysis" ? currentAnalysis(request) : null;
    const anonymous = request.cookies.get("aphrodize_anonymous")?.value;
    const separator = anonymous?.indexOf(":") ?? -1;
    const anonymousToken = anonymous && separator > 0 && UUID.test(anonymous.slice(0, separator))
      && /^[\w.-]+$/.test(anonymous.slice(separator + 1)) ? anonymous.slice(separator + 1) : null;
    const token = request.cookies.get(SESSION_COOKIE)?.value ?? anonymousToken;
    if (request.nextUrl.searchParams.get("scope") === "analysis" && (!analysisId || !token)) {
      return failed(401, "No active analysis in this browser");
    }
    const username = process.env.BACKEND_API_USERNAME;
    const password = process.env.BACKEND_API_PASSWORD;
    if (!analysisId && (!username || !password)) throw new Error("Backend credentials are not configured");
    const response = await fetch(
      `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/analyses/${analysisId ? `${analysisId}/recommendations` : "recommendations/guest"}?${query}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: analysisId ? `Bearer ${token}` : `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` },
        body: JSON.stringify(answers), cache: "no-store",
      },
    );
    const body = await response.json().catch(() => null);
    if (!response.ok) return failed(response.status, typeof body?.detail === "string" ? body.detail : "ข้อมูลผิวไม่ครบถ้วนหรือโหลดคำแนะนำไม่สำเร็จ");
    return NextResponse.json(body, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return failed(502, "ยังเชื่อมต่อบริการคำแนะนำไม่ได้");
  }
}
