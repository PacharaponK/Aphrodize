import type { Metadata } from "next";
import Link from "next/link";
import { RecommendationPanel } from "./recommendation-panel";
import { WorkspaceShell } from "@/components/workspace-shell";

export const metadata: Metadata = { title: "คำแนะนำ — Aphrodize" };

export default function Page() {
  return (
    <WorkspaceShell active="none" eyebrow="SKIN ANALYSIS GUIDANCE" title="คำแนะนำจากผลวิเคราะห์ผิว">
      <section className="page-content workspace-panel">
        <p className="eyebrow">คำแนะนำจากผลผิว</p>
        <h2>หมวดผลิตภัณฑ์ที่อาจตรงกับผลวิเคราะห์และข้อมูลที่รายงาน</h2>
        <p>ใช้ผลภาพต่อเมื่อผ่านเกณฑ์ที่เผยแพร่แล้ว และแสดงแยกจากคำแนะนำที่หน้าโปรไฟล์</p>
        <RecommendationPanel source="analysis" />
        <div className="page-actions">
          <Link className="secondary-button" href="/result-detail">กลับผลรายบริเวณ</Link>
          <Link className="primary-button" href="/capture">ถ่ายภาพครั้งถัดไป →</Link>
        </div>
      </section>
    </WorkspaceShell>
  );
}
