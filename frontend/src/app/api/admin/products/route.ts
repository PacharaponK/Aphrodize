import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";
import { adminConfigured, hasAdminSession, sameOrigin } from "@/lib/admin-auth";

export const runtime = "nodejs";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function forward(request: NextRequest, method: "GET" | "POST" | "PUT" | "PATCH") {
  if (!adminConfigured()) return NextResponse.json({ detail: "Admin access is not configured" }, { status: 503 });
  if (!hasAdminSession(request)) return NextResponse.json({ detail: "กรุณาเข้าสู่ระบบแอดมิน" }, { status: 401 });
  if (method !== "GET" && !sameOrigin(request)) {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  }
  if (method !== "GET" && Number(request.headers.get("content-length")) > 30_000) {
    return NextResponse.json({ detail: "Request too large" }, { status: 413 });
  }
  const body = method === "GET" ? null : await request.json().catch(() => null);
  if (method !== "GET" && (!body || typeof body !== "object" || Array.isArray(body))) {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }
  const id = body?.id;
  if ((method === "PUT" || method === "PATCH") && (typeof id !== "string" || !UUID.test(id))) {
    return NextResponse.json({ detail: "Invalid product id" }, { status: 400 });
  }
  const path = method === "PUT" ? `/${id}` : method === "PATCH" ? `/${id}/status` : "";
  const payload = { ...body };
  delete payload.id;
  try {
    const response = await fetch(`${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/admin/products${path}`, {
      method,
      headers: {
        Authorization: `Basic ${Buffer.from(`${process.env.ADMIN_USERNAME}:${process.env.ADMIN_PASSWORD}`).toString("base64")}`,
        ...(method === "GET" ? {} : { "Content-Type": "application/json" }),
      },
      body: method === "GET" ? undefined : JSON.stringify(payload),
      cache: "no-store",
    });
    const result = await response.json().catch(() => ({ detail: "Backend request failed" }));
    return NextResponse.json(result, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "เชื่อมต่อบริการสินค้าไม่ได้" }, { status: 502 });
  }
}

export async function GET(request: NextRequest) { return forward(request, "GET"); }
export async function POST(request: NextRequest) { return forward(request, "POST"); }
export async function PUT(request: NextRequest) { return forward(request, "PUT"); }
export async function PATCH(request: NextRequest) { return forward(request, "PATCH"); }
