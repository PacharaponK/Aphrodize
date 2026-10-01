import { pageMetadata } from "@/lib/page-metadata";
import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";

export const metadata = pageMetadata(
  "ตัวอย่างหน้าจอ",
  "สำรวจตัวอย่างหน้าจอและขั้นตอนการใช้งาน Aphrodize ตั้งแต่เข้าสู่ระบบ ถ่ายภาพ ตรวจคุณภาพภาพ ไปจนถึงผลการวิเคราะห์และคำแนะนำ",
  "/showcase",
  false,
  "th_TH",
);

const pages = [
  ["Login", "/login"],
  ["Dashboard", "/"],
  ["Capture guide", "/capture"],
  ["Quality rejected", "/quality-rejected"],
  ["Results and recommendations", "/capture#results"],
];

export default function Page() {
  return (
    <WorkspaceShell eyebrow="UI FLOWS" title="ตัวอย่างหน้าจอ">
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
