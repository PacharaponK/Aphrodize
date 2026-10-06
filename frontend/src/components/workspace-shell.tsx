"use client";

import { type ReactNode } from "react";
import { useLanguage } from "./language-provider";

const englishTitles: Record<string, string> = {
  "วิเคราะห์ภาพ": "Analyze image",
  "โปรไฟล์ผิวของคุณ": "Your skin profile",
  "คำแนะนำ": "Guidance",
  "คำแนะนำจากผลวิเคราะห์ผิว": "Skin analysis guidance",
  "ผลวิเคราะห์ใบหน้า": "Face analysis results",
  "ตรวจคุณภาพภาพ": "Image quality check",
  "ตัวอย่างหน้าจอ": "UI preview",
};

const englishDetails: Record<string, string> = {
  "ขั้นตอน 1 จาก 2 · เตรียมภาพ": "Step 1 of 2 · Prepare image",
};

export function WorkspaceShell({ eyebrow, title, detail, children, className = "" }: {
  eyebrow: string;
  title: string;
  detail?: string;
  children: ReactNode;
  className?: string;
}) {
  const { language } = useLanguage();

  return (
    <div className={`app-shell workspace-shell${className ? ` ${className}` : ""}`}>
      <main className="workspace-main">
        <header className="topbar workspace-topbar">
          <div><p className="eyebrow">{eyebrow}</p><h1>{language === "en" ? englishTitles[title] ?? title : title}</h1></div>
          <div className="workspace-header-actions">
            {detail && <span className="workspace-detail">{language === "en" ? englishDetails[detail] ?? detail : detail}</span>}
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
