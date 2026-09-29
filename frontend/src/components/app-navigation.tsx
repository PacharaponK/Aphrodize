"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, Camera, House, Menu, TrendingUp, UserRound, X } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

type ActiveSection = "dashboard" | "capture" | "clients" | "trend" | "profile" | "none";

const navigationItems = [
  { id: "dashboard", href: "#dashboard", label: "ภาพรวม", Icon: House },
  { id: "capture", href: "/capture", label: "วิเคราะห์ภาพ", Icon: Camera },
  { id: "clients", href: "/clients", label: "สุขภาพรายวัน", Icon: Activity },
  { id: "trend", href: "/trend", label: "แนวโน้ม", Icon: TrendingUp },
  { id: "profile", href: "/profile", label: "Skin profile", Icon: UserRound },
] as const;

const englishNavigation = { dashboard: "Overview", capture: "Analyze image", clients: "Daily health", trend: "Trends", profile: "Skin profile" };

export function AppNavigation({ active, showThemeToggle = false, initialLanguage = "th" }: { active: ActiveSection; showThemeToggle?: boolean; initialLanguage?: "th" | "en" }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [language, setLanguage] = useState(initialLanguage);
  const dashboardHref = active === "dashboard" ? "#dashboard" : "/#dashboard";

  useEffect(() => {
    if (active !== "dashboard") return;
    const syncLanguage = () => setLanguage(localStorage.getItem("aphrodize-language") === "th" ? "th" : "en");
    syncLanguage();
    window.addEventListener("aphrodize-language-change", syncLanguage);
    return () => window.removeEventListener("aphrodize-language-change", syncLanguage);
  }, [active]);

  useEffect(() => {
    if (!mobileOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
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
          type="button"
          className="app-nav-toggle"
          aria-label={language === "en" ? (mobileOpen ? "Close menu" : "Open menu") : (mobileOpen ? "ปิดเมนู" : "เปิดเมนู")}
          aria-controls="primary-navigation"
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
        {showThemeToggle && <ThemeToggle className="app-navigation-theme-toggle" />}
      </div>
    </header>
  );
}
