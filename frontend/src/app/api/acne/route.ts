import { NextRequest, NextResponse } from "next/server";
import { accountSession, backendUrl, sameOrigin } from "@/lib/daily-health-session";

export const runtime = "nodejs";
const headers = { "Cache-Control": "no-store" };
function fail(status: number, detail: string) {
  return NextResponse.json({ detail }, { status, headers });
}
async function proxy(request: NextRequest, method: string) {
  if (method !== "GET" && !sameOrigin(request)) return fail(403, "Invalid request origin");
  try {
    const account = await accountSession(request);
    if (!account) return fail(401, "Please sign in");
    let suffix = "";
    const scope = request.nextUrl.searchParams.get("scope");
    if (scope !== null && scope !== "training") return fail(400, "Invalid consent scope");
    if (scope !== null && method !== "PUT" && method !== "DELETE") return fail(400, "Invalid consent method");
    if (scope === "training" && method === "PUT") return fail(410, "Acne model training has been removed");
    let body: unknown;
    if (method === "POST") {
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > 4096) return fail(413, "Body too large");
      try { body = JSON.parse(raw); } catch { return fail(400, "Invalid JSON"); }
      suffix = "/observations";
    } else if (method === "PUT") {
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > 4096) return fail(413, "Body too large");
      try { body = JSON.parse(raw); } catch { return fail(400, "Invalid JSON"); }
      suffix = scope === "training" ? "/training-consent" : "/consent";
    } else if (method === "DELETE") {
      const date = request.nextUrl.searchParams.get("date");
      if (scope === "training" && date !== null) return fail(400, "Conflicting request targets");
      if (date !== null && !/^\d{4}-\d{2}-\d{2}$/.test(date)) return fail(400, "Invalid date");
      suffix = scope === "training" ? "/training-consent" : date === null ? "/consent" : `/observations/${date}`;
    }
    const response = await fetch(backendUrl(`/acne/users/${account.userId}${suffix}`), {
      method: method === "POST" ? "PUT" : method,
      headers: { Authorization: `Bearer ${account.token}`, "Content-Type": "application/json" },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}), cache: "no-store",
    });
    if (response.status === 204) return new NextResponse(null, { status: 204, headers });
    if (!response.ok) return fail(response.status, response.status === 403 ? "Required consent is not active" : "Could not complete acne request");
    return NextResponse.json(await response.json(), { headers });
  } catch { return fail(503, "Acne service unavailable"); }
}
export const GET = (request: NextRequest) => proxy(request, "GET");
export const POST = (request: NextRequest) => proxy(request, "POST");
export const PUT = (request: NextRequest) => proxy(request, "PUT");
export const DELETE = (request: NextRequest) => proxy(request, "DELETE");
