import { backendFetch as fetch } from "@/lib/backend-fetch";
import "server-only";

export async function GET(): Promise<Response> {
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  const headers = { "Cache-Control": "no-store" };
  if (!username || !password) {
    return Response.json({ detail: "ยังไม่ได้ตั้งค่าการเชื่อมต่อ API" }, { status: 503, headers });
  }
  try {
    const upstream = await fetch(
      `${(process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")}/api/v1/uv/products`,
      {
        headers: { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` },
        cache: "no-store", signal: AbortSignal.timeout(15_000),
      },
    );
    return Response.json(await upstream.json(), { status: upstream.status, headers });
  } catch {
    return Response.json({ detail: "โหลดรายการกันแดดไม่ได้" }, { status: 503, headers });
  }
}
