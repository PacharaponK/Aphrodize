import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";
import { adminConfigured, hasAdminSession, sameOrigin } from "@/lib/admin-auth";

export const runtime = "nodejs";

async function forward(request: NextRequest, method: "GET" | "POST") {
  const reply = (body: unknown, status: number) => NextResponse.json(body, { status, headers: { "Cache-Control": "no-store" } });
  if (!adminConfigured()) return reply({ detail: "ยังไม่ได้ตั้งค่าบัญชีแอดมิน" }, 503);
  if (!hasAdminSession(request)) return reply({ detail: "Session หมดอายุ กรุณาเข้าสู่ระบบแอดมินอีกครั้ง" }, 401);
  if (method === "POST" && (!request.headers.get("origin") || !sameOrigin(request))) return reply({ detail: "Invalid request origin" }, 403);
  let body: string | undefined;
  if (method === "POST") {
    if (Number(request.headers.get("content-length")) > 4096) return reply({ detail: "Request too large" }, 413);
    body = await request.text();
    if (Buffer.byteLength(body) > 4096) return reply({ detail: "Request too large" }, 413);
    try { JSON.parse(body); } catch { return reply({ detail: "Invalid JSON" }, 400); }
  }
  try {
    const response = await fetch(`${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/admin/uv`, {
      method, body, cache: "no-store",
      headers: {
        Authorization: `Basic ${Buffer.from(`${process.env.ADMIN_USERNAME}:${process.env.ADMIN_PASSWORD}`).toString("base64")}`,
        ...(method === "POST" ? { "Content-Type": "application/json" } : {}),
      },
    });
    return reply(await response.json().catch(() => ({ detail: "บริการ UV ส่งข้อมูลไม่สำเร็จ" })), response.status);
  } catch {
    return reply({ detail: "เชื่อมต่อบริการ UV ไม่ได้ กรุณาลองใหม่" }, 502);
  }
}

export async function GET(request: NextRequest) { return forward(request, "GET"); }
export async function POST(request: NextRequest) { return forward(request, "POST"); }
