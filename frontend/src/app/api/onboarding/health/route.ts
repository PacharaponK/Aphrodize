import { backendFetch as fetch } from "@/lib/backend-fetch";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const SESSION_COOKIE = "aphrodize_session";

function backendUrl(safetyOnly: boolean): string {
  const suffix = safetyOnly ? "/initial/safety" : "/initial";
  return `${process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000"}/api/v1/questionnaires${suffix}`;
}

function detailMessage(detail: unknown): string {
  return typeof detail === "string" ? detail : "บันทึกแบบสอบถามไม่สำเร็จ โปรดลองอีกครั้ง";
}

async function forward(request: NextRequest, method: "GET" | "POST" | "PUT"): Promise<NextResponse> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && (!host || origin !== `${request.nextUrl.protocol}//${host}`)) {
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  }
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "กรุณาสมัครสมาชิกหรือเข้าสู่ระบบก่อน" }, { status: 401 });
  }
  try {
    const payload = method === "GET" ? undefined : await request.json();
    const safetyOnly = request.nextUrl.searchParams.get("safety") === "1";
    if (safetyOnly && method !== "PUT") return NextResponse.json({ detail: "Safety screening must be updated with PUT" }, { status: 405 });
    const response = await fetch(backendUrl(safetyOnly), {
      method,
      headers: {
        "Authorization": `Bearer ${token}`,
        ...(method === "GET" ? {} : { "Content-Type": "application/json" }),
      },
      ...(method === "GET" ? {} : { body: JSON.stringify(payload) }),
      cache: "no-store",
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return NextResponse.json(
        { detail: detailMessage(body?.detail) },
        { status: response.status, headers: { "Cache-Control": "no-store" } },
      );
    }
    return NextResponse.json(body, { status: method === "POST" ? 201 : 200, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json(
      { detail: "ยังเชื่อมต่อบริการแบบสอบถามไม่ได้ กรุณาลองใหม่อีกครั้ง" },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  return forward(request, "POST");
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  return forward(request, "GET");
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  return forward(request, "PUT");
}
