import "server-only";

const cities = new Set(["bangkok", "songkhla", "chiang_mai"]);

export async function GET(request: Request): Promise<Response> {
  const city = new URL(request.url).searchParams.get("city");
  if (!city || !cities.has(city)) {
    return Response.json({ detail: "เลือกพื้นที่ที่รองรับ" }, { status: 400 });
  }
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  if (!username || !password) {
    return Response.json({ detail: "ยังไม่ได้ตั้งค่าการเชื่อมต่อ API" }, { status: 503 });
  }
  try {
    const upstream = await fetch(
      `${(process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")}/api/v1/uv/recommendation?city=${city}`,
      { headers: { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` }, cache: "no-store" },
    );
    const payload = await upstream.json().catch(() => ({ detail: "API ส่งข้อมูลไม่ถูกต้อง" }));
    return Response.json(payload, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ detail: "เชื่อมต่อบริการ UV ไม่ได้" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
