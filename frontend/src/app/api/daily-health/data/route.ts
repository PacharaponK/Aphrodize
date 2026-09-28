import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  const headers = { "Cache-Control": "no-store" };
  if (!sameOrigin(request)) {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403, headers });
  }
  try {
    const account = await accountSession(request);
    if (!account) {
      return NextResponse.json({ detail: "Please sign in to delete daily health data" }, { status: 401, headers });
    }
    const response = await fetch(backendUrl(`/daily-health/users/${account.userId}/data`), {
      method: "DELETE",
      headers: { Authorization: `Bearer ${account.token}` },
      cache: "no-store",
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      return NextResponse.json(
        { detail: typeof body?.detail === "string" ? body.detail : "Could not delete daily health data" },
        { status: response.status, headers },
      );
    }
    return new NextResponse(null, { status: 204, headers });
  } catch {
    return NextResponse.json({ detail: "Could not delete daily health data" }, { status: 503, headers });
  }
}
