import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const supplied = request.headers.get("x-request-id");
  const id = supplied && /^[0-9a-f]{32}$/i.test(supplied)
    ? supplied.toLowerCase() : randomUUID().replaceAll("-", "");
  const headers = new Headers(request.headers);
  headers.set("x-request-id", id);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("x-request-id", id);
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
