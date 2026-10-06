import type { NextRequest } from "next/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function backendUrl(path: string): string {
  return `${(process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")}/api/v1${path}`;
}

export function apiHeaders(): HeadersInit {
  const username = process.env.BACKEND_API_USERNAME;
  const password = process.env.BACKEND_API_PASSWORD;
  if (!username || !password) throw new Error("Backend credentials are not configured");
  return { Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}` };
}

export async function accountSession(request: NextRequest): Promise<{
  userId: string;
  token: string;
  sex?: "male" | "female" | "prefer_not_to_say" | null;
} | null> {
  const token = request.cookies.get("aphrodize_session")?.value;
  if (!token) return null;
  const response = await fetch(backendUrl("/auth/profile"), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error("Could not verify account session");
  const profile: unknown = await response.json();
  if (typeof profile !== "object" || profile === null || !("user_id" in profile)
    || typeof profile.user_id !== "string" || !UUID.test(profile.user_id)) {
    throw new Error("Backend returned an invalid account identity");
  }
  const savedProfile = "profile" in profile ? profile.profile : null;
  const savedSex = typeof savedProfile === "object" && savedProfile !== null && "sex" in savedProfile
    ? savedProfile.sex : null;
  const sex = savedSex === "male" || savedSex === "female" || savedSex === "prefer_not_to_say"
    ? savedSex : null;
  return { userId: profile.user_id, token, sex };
}

export function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  return !origin || Boolean(host && origin === `${request.nextUrl.protocol}//${host}`);
}
