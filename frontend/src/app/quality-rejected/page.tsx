"use client";

import type { Metadata } from "next";
import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useLanguage } from "@/components/language-provider";

export const metadata: Metadata = { title: "ภาพยังไม่ผ่าน — Aphrodize" };

export default function Page() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  return (
    <WorkspaceShell active="capture" eyebrow="QUALITY GATE" title="ตรวจคุณภาพภาพ">
      <section className="page-content workspace-panel quality-panel">
        <div className="quality-symbol">!</div>
        <p className="eyebrow">QUALITY GATE</p>
        <h2>{t("ภาพนี้ยังใช้เปรียบเทียบไม่ได้", "This image cannot be compared")}</h2>
        <p>{t("จึงไม่นำไปคำนวณผลหรือแนวโน้ม เพื่อไม่ให้ความต่างของภาพถูกตีความว่าเป็นความเปลี่ยนแปลงของผิว", "It will not be used to calculate a result or trend, so image differences are not mistaken for skin changes.")}</p>
        <ul className="quality-list"><li>{t("แสงน้อยเกินไป", "Lighting is too low")}</li><li>{t("ภาพอาจเบลอ", "The image may be blurry")}</li></ul>
        <p className="metadata">{t("ลองหันหน้าเข้าหาแสงนุ่มที่สม่ำเสมอ และวางกล้องให้นิ่ง", "Face soft, even lighting and hold the camera steady.")}</p>
        <div className="page-actions"><Link className="primary-button" href="/capture">{t("ถ่ายภาพใหม่ →", "Take a new photo →")}</Link><Link className="secondary-button" href="/">{t("กลับหน้าภาพรวม", "Back to overview")}</Link></div>
      </section>
    </WorkspaceShell>
  );
}
