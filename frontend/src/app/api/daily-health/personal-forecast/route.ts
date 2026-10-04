import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

type ConsentAction = "GET" | "PUT" | "DELETE";

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

async function forwardPersonalForecast(
  request: NextRequest,
  method: ConsentAction,
): Promise<NextResponse> {
  if (method !== "GET" && !sameOrigin(request)) {
    return failed(403, "Invalid request origin");
  }

  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "Please sign in to view personal forecasts");

    const isConsentAction = method !== "GET";
    const response = await fetch(
      backendUrl(
        `/daily-health/users/${account.userId}/${isConsentAction ? "personal-forecast-consent" : "personal-forecast"}`,
      ),
      {
        method,
        headers: { Authorization: `Bearer ${account.token}` },
        cache: "no-store",
      },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      return failed(
        response.status,
        typeof body?.detail === "string" ? body.detail : "Could not load personal forecast",
      );
    }
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        headers: { "Cache-Control": "no-store" },
      });
    }
    return NextResponse.json(await response.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return failed(503, "Could not reach the personal forecast service");
  }
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  return forwardPersonalForecast(request, "GET");
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  return forwardPersonalForecast(request, "PUT");
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  return forwardPersonalForecast(request, "DELETE");
}
