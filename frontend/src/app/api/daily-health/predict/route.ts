import { forwardDailyHealthPrediction } from "@/lib/daily-health-prediction";

const MAX_BODY_BYTES = 16_384;

function failure(status: number, detail: string): Response {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function POST(request: Request): Promise<Response> {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin) {
    const originUrl = new URL(origin);
    const requestUrl = new URL(request.url);
    const forwardedHost = request.headers.get("x-forwarded-host");
    const allowedHosts = new Set([host, forwardedHost, requestUrl.host].filter(Boolean));
    const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",")[0];
    const expectedProtocol = forwardedProtocol
      ? `${forwardedProtocol.trim()}:`
      : requestUrl.protocol;
    if (!allowedHosts.has(originUrl.host) || originUrl.protocol !== expectedProtocol) {
      return failure(403, "Invalid request origin");
    }
  }
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BODY_BYTES) return failure(413, "Request body is too large");

  let body: string;
  try {
    body = await request.text();
  } catch {
    return failure(400, "Expected a JSON request body");
  }
  if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES) {
    return failure(413, "Request body is too large");
  }

  const upstream = await forwardDailyHealthPrediction(body);
  return Response.json(upstream.payload, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}
