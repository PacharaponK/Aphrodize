"use client";

import { useEffect, useRef, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { useLanguage } from "./language-provider";

export function HomeRevealFooter({ children }: { children: ReactNode }) {
  const frame = useRef<HTMLDivElement>(null);
  const footer = useRef<HTMLElement>(null);
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;

  useEffect(() => {
    const root = frame.current;
    const element = footer.current;
    if (!root || !element || typeof ResizeObserver === "undefined") return;
    const desktop = window.matchMedia("(min-width: 961px) and (pointer: fine)");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      root.dataset.reveal = String(desktop.matches && !reduced.matches && element.getBoundingClientRect().height < window.innerHeight - 120);
    };
    const observer = new ResizeObserver(update);
    observer.observe(element);
    window.addEventListener("resize", update);
    desktop.addEventListener("change", update);
    reduced.addEventListener("change", update);
    update();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
      desktop.removeEventListener("change", update);
      reduced.removeEventListener("change", update);
      delete root.dataset.reveal;
    };
  }, []);

  return <div className="home-reveal-frame" ref={frame}>
    <div className="home-reveal-content">{children}</div>
    <footer className="home-reveal-footer" ref={footer}>
      <div className="home-footer-inner">
        <div className="home-footer-brand">
          <Link href="/#dashboard" aria-label={t("หน้าภาพรวม Aphrodize", "Aphrodize overview")}>
            <Image className="brand-mark-light" src="/assets/aphrodize-logo.svg" width={44} height={54} alt="" unoptimized />
            <Image className="brand-mark-dark" src="/assets/aphrodize-logo-dark.svg" width={44} height={54} alt="" unoptimized />
            <span>Aphrodize</span>
          </Link>
          <p>{t("รู้จักผิว ผ่านเรื่องราวในทุกวัน", "Your skin. Your daily story.")}</p>
        </div>
        <nav className="home-footer-links" aria-label={t("ทางลัดท้ายหน้า", "Footer shortcuts")}>
          <Link href="/capture">{t("วิเคราะห์ภาพ", "Analyze image")}</Link>
          <Link href="/clients">{t("สุขภาพรายวัน", "Daily health")}</Link>
          <Link href="/trend">{t("ประวัติและแนวโน้ม", "History & trends")}</Link>
          <Link href="/profile">{t("ข้อมูลผิว", "Skin profile")}</Link>
          <Link href="/uv-map">{t("แผนที่ UV", "Explore UV map")}</Link>
        </nav>
        <p className="home-footer-safety">{t("เพื่อการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์", "Personal tracking, not a medical diagnosis.")}</p>
      </div>
    </footer>
  </div>;
}
