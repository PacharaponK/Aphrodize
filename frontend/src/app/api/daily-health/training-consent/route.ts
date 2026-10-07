import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";

function failed(status: number, detail: string): NextResponse {
  return NextResponse.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  if (!sameOrigin(request)) {
    return failed(403, "Invalid request origin");
  }
  try {
    const account = await accountSession(request);
    if (!account) return failed(401, "Please sign in to change training consent");
    const response = await fetch(
      backendUrl(`/daily-health/users/${account.userId}/training-consent`),
      { method: "DELETE", headers: { Authorization: `Bearer ${account.token}` }, cache: "no-store" },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      return failed(
        response.status,
        typeof body?.detail === "string" ? body.detail : "Could not revoke model-training consent",
      );
    }
    return new NextResponse(null, { status: 204 });
  } catch {
    return failed(503, "Could not revoke model-training consent");
  }
}
