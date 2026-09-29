import "server-only";

type ForwardResult = { status: number; payload: unknown };

export function todayInBangkok(): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Bangkok",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

export async function forwardDailyHealthPrediction(
  body: string,
  options: { testOnly?: boolean } = {},
): Promise<ForwardResult> {
  const apiBase = (process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;

  if (!username || !password) {
    return { status: 503, payload: { detail: "Backend API credentials are not configured" } };
  }

  try {
    const endpoint = options.testOnly ? "predict/test" : "predict";
    const upstream = await fetch(`${apiBase}/api/v1/daily-health/${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}`,
      },
      body,
      cache: "no-store",
    });
    const payload = await upstream.json().catch(() => ({ detail: "Prediction API returned invalid JSON" }));
    return { status: upstream.status, payload };
  } catch {
    return {
      status: 503,
      payload: { detail: "Daily prediction API is unavailable. Check that the backend is running." },
    };
  }
}
