import type { Metadata } from "next";
import Link from "next/link";
import { RecommendationPanel } from "./recommendation-panel";
import { WorkspaceShell } from "@/components/workspace-shell";

export const metadata: Metadata = { title: "คำแนะนำ — Aphrodize" };

export default function Page() {
  return (
    <WorkspaceShell eyebrow="SKIN ANALYSIS GUIDANCE" title="คำแนะนำจากผลวิเคราะห์ผิว">
      <section className="page-content workspace-panel">
        <p className="eyebrow">คำแนะนำจากผลผิว</p>
        <h2>ผลิตภัณฑ์ที่ตรงกับข้อมูลผิวของคุณ</h2>
        <p>หลังวิเคราะห์ภาพสำเร็จ ระบบใช้โปรไฟล์ล่าสุด ประวัติแพ้ และแค็ตตาล็อกที่ตรวจทานแล้ว โดยใช้บริเวณริ้วรอยประกอบเฉพาะผลภาพที่ผ่านเกณฑ์การเผยแพร่</p>
        <RecommendationPanel source="analysis" />
        <div className="page-actions">
          <Link className="secondary-button" href="/result-detail">กลับผลรายบริเวณ</Link>
          <Link className="primary-button" href="/capture">ถ่ายภาพครั้งถัดไป →</Link>
        </div>
      </section>
    </WorkspaceShell>
  );
}
