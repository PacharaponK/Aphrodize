import type { Metadata } from "next";
import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";

export const metadata: Metadata = { title: "Aphrodize — UI preview" };

const pages = [
  ["Login", "/login"],
  ["Dashboard", "/"],
  ["Capture guide", "/capture"],
  ["Quality rejected", "/quality-rejected"],
  ["Result detail", "/result-detail"],
  ["Recommendation", "/recommendation"],
];

export default function Page() {
  return (
    <WorkspaceShell active="none" eyebrow="UI FLOWS" title="ตัวอย่างหน้าจอ">
      <section className="page-content workspace-panel">
        <p className="eyebrow">UI FLOWS</p>
        <h2>เลือกหน้าที่ต้องการดู</h2>
        <p>ตัวอย่างหน้าจอใน Next.js บางหน้ายังใช้ข้อมูลตัวอย่าง</p>
        <div className="showcase-grid">
          {pages.map(([label, href], index) => <Link href={href} key={href}><span>{String(index + 1).padStart(2, "0")}</span><strong>{label}</strong></Link>)}
        </div>
      </section>
    </WorkspaceShell>
  );
}
