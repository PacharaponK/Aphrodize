import type { Metadata } from "next";
import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";

export const metadata: Metadata = { title: "ภาพยังไม่ผ่าน — Aphrodize" };

export default function Page() {
  return (
    <WorkspaceShell active="capture" eyebrow="QUALITY GATE" title="ตรวจคุณภาพภาพ">
      <section className="page-content workspace-panel quality-panel">
        <div className="quality-symbol">!</div>
        <p className="eyebrow">QUALITY GATE</p>
        <h2>ภาพนี้ยังใช้เปรียบเทียบไม่ได้</h2>
        <p>จึงไม่นำไปคำนวณผลหรือแนวโน้ม เพื่อไม่ให้ความต่างของภาพถูกตีความว่าเป็นความเปลี่ยนแปลงของผิว</p>
        <ul className="quality-list"><li>แสงน้อยเกินไป</li><li>ภาพอาจเบลอ</li></ul>
        <p className="metadata">ลองหันหน้าเข้าหาแสงนุ่มที่สม่ำเสมอ และวางกล้องให้นิ่ง</p>
        <div className="page-actions"><Link className="primary-button" href="/capture">ถ่ายภาพใหม่ →</Link><Link className="secondary-button" href="/">กลับหน้าภาพรวม</Link></div>
      </section>
    </WorkspaceShell>
  );
}
