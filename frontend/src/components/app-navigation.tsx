"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Activity, Camera, House, LogIn, LogOut, Menu, TrendingUp, UserRound, X } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { LanguageToggle, useLanguage } from "./language-provider";

type ActiveSection = "dashboard" | "capture" | "clients" | "trend" | "profile" | "none";

const navigationItems = [
  { id: "dashboard", href: "#dashboard", label: "ภาพรวม", Icon: House },
  { id: "capture", href: "/capture", label: "วิเคราะห์ภาพ", Icon: Camera },
  { id: "clients", href: "/clients", label: "สุขภาพรายวัน", Icon: Activity },
  { id: "trend", href: "/trend", label: "แนวโน้ม", Icon: TrendingUp },
  { id: "profile", href: "/profile", label: "โปรไฟล์ผิว", Icon: UserRound },
] as const;

const englishNavigation = { dashboard: "Overview", capture: "Analyze image", clients: "Daily health", trend: "Trends", profile: "Skin profile" };

type AuthStatus = "checking" | "signed-in" | "signed-out";

export function AuthNavigationAction({
  language,
  authStatus,
  showSignIn,
  signingOut,
  logoutError,
  onSignOut,
}: {
  language: "th" | "en";
  authStatus: AuthStatus;
  showSignIn: boolean;
  signingOut: boolean;
  logoutError: string;
  onSignOut: () => void;
}) {
  if (authStatus === "signed-in") {
    const label = signingOut
      ? language === "en" ? "Signing out…" : "กำลังออกจากระบบ…"
      : language === "en" ? "Log out" : "ออกจากระบบ";
    return (
      <>
        <button
          type="button"
          className="app-navigation-auth-action app-navigation-sign-out"
          aria-label={label}
          title={label}
          disabled={signingOut}
          onClick={onSignOut}
        >
          <LogOut aria-hidden="true" size={18} />
          <span>{label}</span>
        </button>
        {logoutError && <span className="app-navigation-auth-error" role="alert">{logoutError}</span>}
      </>
    );
  }

  if (!showSignIn) return null;

  const label = language === "en" ? "Sign in" : "เข้าสู่ระบบ";
  return (
    <Link
      className="app-navigation-auth-action app-navigation-sign-in"
      href="/login"
      aria-label={label}
      title={label}
    >
      <LogIn aria-hidden="true" size={18} />
      <span>{label}</span>
    </Link>
  );
}

export function AppNavigation({ active, showThemeToggle = false, showSignIn = false }: {
  active: ActiveSection;
  showThemeToggle?: boolean;
  showSignIn?: boolean;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus>("checking");
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const { language } = useLanguage();
  const dashboardHref = active === "dashboard" ? "#dashboard" : "/#dashboard";

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/profile", { cache: "no-store", signal: controller.signal })
      .then((response) => {
        if (response.ok) setAuthStatus("signed-in");
        else if (response.status === 401) setAuthStatus("signed-out");
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  async function signOut() {
    setSigningOut(true);
    setLogoutError("");
    try {
      const response = await fetch("/api/auth/logout", { method: "POST", cache: "no-store" });
      if (!response.ok) throw new Error("Logout failed");
      setAuthStatus("signed-out");
      setMobileOpen(false);
      // Reload so private client-side data is discarded along with the session cookie.
      window.location.replace("/");
    } catch {
      setLogoutError(language === "en" ? "Could not log out. Try again." : "ออกจากระบบไม่สำเร็จ กรุณาลองอีกครั้ง");
      setSigningOut(false);
    }
  }

  useEffect(() => {
    if (!mobileOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        menuButton.current?.focus();
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [mobileOpen]);

  return (
    <header className={`app-navigation${mobileOpen ? " is-open" : ""}`}>
      <div className="app-navigation-inner">
        <Link className="brand" href={dashboardHref} aria-label="Aphrodize home" onClick={() => setMobileOpen(false)}>
          <Image width={50} height={50} className="brand-mark" src="/assets/aphrodize-logo.svg" alt="" unoptimized />
          <span>Aphrodize</span>
        </Link>
        <button
          ref={menuButton}
          type="button"
          className="app-nav-toggle"
          aria-label={language === "en" ? (mobileOpen ? "Close menu" : "Open menu") : (mobileOpen ? "ปิดเมนู" : "เปิดเมนู")}
          aria-controls="primary-navigation navigation-controls"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((isOpen) => !isOpen)}
        >
          {mobileOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
        <nav id="primary-navigation" className="app-navigation-links" aria-label={language === "en" ? "Primary navigation" : "เมนูหลัก"}>
          {navigationItems.map(({ id, href, label, Icon }) => {
            const isActive = active === id;
            const itemHref = id === "dashboard" ? dashboardHref : href;

            return (
              <Link
                key={id}
                className={`nav-link${isActive ? " active" : ""}`}
                href={itemHref}
                aria-current={isActive ? "page" : undefined}
                onClick={() => setMobileOpen(false)}
              >
                <Icon className="nav-icon" aria-hidden="true" />
                <span className="nav-label" data-nav-label={id}>{language === "en" ? englishNavigation[id] : label}</span>
              </Link>
            );
          })}
        </nav>
        <div id="navigation-controls" className="app-navigation-controls">
          <LanguageToggle className="app-navigation-language-toggle" />
          {showThemeToggle && <ThemeToggle className="app-navigation-theme-toggle" />}
          <AuthNavigationAction
            language={language}
            authStatus={authStatus}
            showSignIn={showSignIn}
            signingOut={signingOut}
            logoutError={logoutError}
            onSignOut={() => void signOut()}
          />
        </div>
      </div>
    </header>
  );
}
