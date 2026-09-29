import { createHash, createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest } from "next/server";

export const ADMIN_COOKIE = "aphrodize_admin";
export const ADMIN_SECONDS = 8 * 60 * 60;

export function adminConfigured(): boolean {
  return Boolean(process.env.ADMIN_USERNAME && (process.env.ADMIN_PASSWORD?.length ?? 0) >= 8);
}

function equal(left: string, right: string): boolean {
  const a = createHash("sha256").update(left).digest();
  const b = createHash("sha256").update(right).digest();
  return timingSafeEqual(a, b);
}

export function validAdminCredentials(username: string, password: string): boolean {
  return adminConfigured() && equal(username, process.env.ADMIN_USERNAME!) && equal(password, process.env.ADMIN_PASSWORD!);
}

function signature(expiry: string): string {
  return createHmac("sha256", process.env.ADMIN_PASSWORD!).update(`admin:${expiry}`).digest("hex");
}

export function adminSessionValue(): string {
  const expiry = String(Date.now() + ADMIN_SECONDS * 1000);
  return `${expiry}.${signature(expiry)}`;
}

export function hasAdminSession(request: NextRequest): boolean {
  if (!adminConfigured()) return false;
  const [expiry, mac] = request.cookies.get(ADMIN_COOKIE)?.value.split(".") ?? [];
  if (!/^\d{13}$/.test(expiry ?? "") || !/^[0-9a-f]{64}$/.test(mac ?? "")) return false;
  if (Date.now() >= Number(expiry)) return false;
  return timingSafeEqual(Buffer.from(mac, "hex"), Buffer.from(signature(expiry), "hex"));
}

export function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  return !origin || Boolean(host && origin === `${request.nextUrl.protocol}//${host}`);
}
