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
  if (origin && origin !== request.nextUrl.origin) return failed(403, "Invalid request origin");
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
    const username = process.env.BACKEND_API_USERNAME;
    const password = process.env.BACKEND_API_PASSWORD;
    if (!username || !password) throw new Error("Backend credentials are not configured");
    const response = await fetch(
      `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/analyses/recommendations/guest?${query}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` },
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
