"use client";

import Image from "next/image";
import Link from "next/link";
import { Camera, House } from "lucide-react";

export function AppNavigation({ active, mobileOpen = false, onClose }: { active: "dashboard" | "capture" | "none"; mobileOpen?: boolean; onClose?: () => void }) {
  const homeHref = active === "dashboard" ? "#dashboard" : "/";

  return (
    <>
      <aside className={`sidebar${mobileOpen ? " mobile-open" : ""}`} aria-label="เมนูหลัก">
        <button type="button" className="sidebar-close" aria-label="ปิดเมนู" onClick={onClose}>×</button>
        <Link className="brand" href="/" aria-label="Aphrodize home">
          <Image width={40} height={40} className="brand-mark" src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize
        </Link>
        <nav>
          <Link className={`nav-link${active === "dashboard" ? " active" : ""}`} href={homeHref} aria-current={active === "dashboard" ? "page" : undefined}><House className="nav-icon" aria-hidden="true" />ภาพรวม</Link>
          <Link className={`nav-link${active === "capture" ? " active" : ""}`} href="/capture" aria-current={active === "capture" ? "page" : undefined}><Camera className="nav-icon" aria-hidden="true" />วิเคราะห์ภาพ</Link>
        </nav>
      </aside>
      <nav className="mobile-nav" aria-label="เมนูมือถือ">
        <Link className={active === "dashboard" ? "active" : ""} href={homeHref} aria-current={active === "dashboard" ? "page" : undefined}><House className="nav-icon" aria-hidden="true" /><span>ภาพรวม</span></Link>
        <Link className={active === "capture" ? "active" : ""} href="/capture" aria-current={active === "capture" ? "page" : undefined}><Camera className="nav-icon" aria-hidden="true" /><span>วิเคราะห์</span></Link>
      </nav>
    </>
  );
}
