import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

async function backendFailure(response: Response): Promise<NextResponse> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : "Daily health profile request failed";
  return failed(response.status, detail);
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const account = await accountSession(request);
    if (!account) {
      return NextResponse.json({
        sex: null,
        has_session: false,
        consent_active: false,
        age_guidance_consent_active: false,
        height_profile_consent_active: false,
        height_cm: null,
        model_training_consent_active: false,
        can_report_outcomes: false,
        age_band: null,
        smoking_status: null,
      }, { headers: { "Cache-Control": "no-store" } });
    }
    const response = await fetch(backendUrl("/daily-health/users/" + account.userId + "/profile"), {
      headers: { Authorization: `Bearer ${account.token}` },
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    const profile = await response.json();
    return NextResponse.json({ has_session: true, ...profile, sex: account.sex ?? null }, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return failed(503, "Could not load personal health settings");
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) {
    return failed(403, "Invalid request origin");
  }

  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "Please sign in to delete daily health settings");
    const response = await fetch(backendUrl("/daily-health/users/" + account.userId + "/profile"), {
      method: "DELETE",
      headers: { Authorization: `Bearer ${account.token}` },
      cache: "no-store",
    });
    if (!response.ok) return backendFailure(response);
    return new NextResponse(null, { status: 204 });
  } catch {
    return failed(503, "Could not delete personal health settings");
  }
}
