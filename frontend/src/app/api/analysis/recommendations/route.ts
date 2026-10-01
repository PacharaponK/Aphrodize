import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const ANALYSIS_COOKIE = "aphrodize_analysis";
const SESSION_COOKIE = "aphrodize_session";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const DEMO_RECOMMENDATION = {
  demo: true,
  status: "ready",
  recommendations: [
    {
      category: "fragrance-free moisturizer",
      rule_id: "R-DRY-001",
      rule_version: "2026-09-28.1",
      rationale: "คุณระบุว่าผิวแห้ง จึงแสดงหมวดมอยส์เจอไรเซอร์ที่ปราศจากน้ำหอม",
      input_source: "self_reported",
      input_fields: ["skin_type"],
      signal_sources: ["self_reported"],
      knowledge_source: {
        id: "aphrodize-category-baseline",
        version: "1.0.0",
        reference: {
          id: "aad-dry-skin",
          title: "American Academy of Dermatology: Dry skin",
          url: "https://www.aad.org/public/everyday-care/skin-care-basics/dry/dermatologists-tips-relieve-dry-skin",
        },
      },
    },
    {
      category: "broad-spectrum sunscreen SPF 30+",
      rule_id: "R-UV-001",
      rule_version: "2026-09-28.1",
      rationale: "คุณรายงานว่าใช้กันแดดไม่สม่ำเสมอและมีกิจกรรมกลางแจ้งสูง",
      input_source: "self_reported_and_daily_health_reported",
      input_fields: ["sunscreen_frequency", "daily_outdoor_exposure_choice"],
      signal_sources: ["self_reported", "daily_health_reported"],
      knowledge_source: {
        id: "aphrodize-category-baseline",
        version: "1.0.0",
        reference: {
          id: "aad-sunscreen",
          title: "American Academy of Dermatology: Sunscreen",
          url: "https://www.aad.org/public/everyday-care/sun-protection/sunscreen-patients",
        },
      },
    },
  ],
  blocked_reason: null,
  image_context: { status: "withheld", reason: "demo_fixture" },
  questionnaire_context: { status: "available", revision_id: "demo-questionnaire" },
  daily_context: {
    status: "available",
    consent: { record_id: "demo-consent", version: "daily-health-v1" },
    lifestyle: {
      source_table: "daily_health_entries",
      record_id: "demo-entry",
      observed_date: "2026-09-30",
      sleep_duration_minutes: 420,
      water_intake_ml: 1500,
      outdoor_exposure_choice: 3,
    },
  },
  rule_version: "2026-09-28.1",
  knowledge_base: { id: "aphrodize-category-baseline", version: "1.0.0" },
  disclaimer: "โหมดสาธิต: ข้อมูลนี้เป็น fixture สำหรับตรวจสอบ UI ไม่ใช่ผลวิเคราะห์หรือคำแนะนำเฉพาะบุคคล",
};

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
  if (request.nextUrl.searchParams.get("demo") === "1") {
    if (process.env.NODE_ENV === "production") return failed(404, "Demo recommendations are disabled");
    return NextResponse.json(DEMO_RECOMMENDATION, { headers: { "Cache-Control": "no-store" } });
  }
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return failed(401, "กรุณาเข้าสู่ระบบเพื่อดูคำแนะนำส่วนบุคคล");
  try {
    const profileScope = request.nextUrl.searchParams.get("scope") === "profile";
    const analysisId = currentAnalysis(request);
    if (!profileScope && !analysisId) return failed(404, "ยังไม่มีผลวิเคราะห์ในเบราว์เซอร์นี้");
    const response = await fetch(
      `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/analyses/${profileScope ? "" : `${analysisId}/`}recommendations`,
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
