import { randomUUID } from "node:crypto";
import { headers } from "next/headers";

// Keep instrumentation at the shared upstream boundary, including caught failures.
export async function backendFetch(input: string | URL, init: RequestInit = {}): Promise<Response> {
  let supplied: string | null = null;
  try { supplied = (await headers()).get("x-request-id"); } catch { /* Non-request callers. */ }
  const id = supplied && /^[0-9a-f]{32}$/i.test(supplied)
    ? supplied.toLowerCase() : randomUUID().replaceAll("-", "");
  const outgoing = new Headers(init.headers);
  outgoing.set("x-request-id", id);
  const timeoutMs = Number(process.env.BACKEND_TIMEOUT_MS ?? 15000);
  const timeout = AbortSignal.timeout(Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 15000);
  const started = performance.now();
  let status = 502;
  try {
    const response = await fetch(input, { ...init, headers: outgoing,
      signal: init.signal ? AbortSignal.any([init.signal, timeout]) : timeout });
    status = response.status;
    return response;
  } finally {
    // No URL/query/body/headers or exception text; IDs bridge to API route logs.
    console.info(JSON.stringify({ timestamp: new Date().toISOString(), service: "frontend",
      environment: process.env.NODE_ENV, event: "backend_request", request_id: id,
      method: init.method ?? "GET", status, duration_seconds: (performance.now() - started) / 1000 }));
  }
}
