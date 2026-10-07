import { backendFetch as fetch } from "@/lib/backend-fetch";
import "server-only";

export async function GET(request: Request): Promise<Response> {
  const day = new URL(request.url).searchParams.get("day") ?? "today";
  const source = new URL(request.url).searchParams.get("source") ?? "api";
  if (source !== "api" && source !== "model") {
    return Response.json({ detail: "เลือกแหล่งข้อมูล API หรือโมเดล" }, { status: 400 });
  }
  if (day !== "today" && day !== "tomorrow") {
    return Response.json({ detail: "เลือกวันนี้หรือพรุ่งนี้" }, { status: 400 });
  }
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  const headers = { "Cache-Control": "no-store" };
  if (!username || !password) {
    return Response.json({ detail: "ยังไม่ได้ตั้งค่าการเชื่อมต่อ API" }, { status: 503, headers });
  }
  try {
    const upstream = await fetch(
      `${(process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")}/api/v1/uv/map?day=${day}&source=${source}`,
      {
        headers: { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` },
        cache: "no-store", signal: AbortSignal.timeout(15_000),
      },
    );
    const payload = await upstream.json();
    return Response.json(payload, { status: upstream.status, headers });
  } catch {
    return Response.json({ detail: "เชื่อมต่อบริการแผนที่ UV ไม่ได้" }, { status: 503, headers });
  }
}
