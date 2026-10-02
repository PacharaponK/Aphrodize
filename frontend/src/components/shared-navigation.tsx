"use client";

import { usePathname } from "next/navigation";
import { AppNavigation } from "./app-navigation";

const sections = {
  "/": "dashboard",
  "/capture": "capture",
  "/clients": "clients",
  "/trend": "trend",
  "/profile": "profile",
  "/quality-rejected": "capture",
  "/showcase": "none",
  "/uv-map": "none",
} as const;

export function SharedNavigation() {
  const pathname = usePathname();
  const active = sections[pathname as keyof typeof sections];
  if (!active) return null;

  return <AppNavigation active={active} showThemeToggle showSignIn={pathname === "/"} />;
}
