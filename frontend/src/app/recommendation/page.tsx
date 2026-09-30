import type { Metadata } from "next";
import Link from "next/link";
import { RecommendationPanel } from "./recommendation-panel";
import { WorkspaceShell } from "@/components/workspace-shell";
import { UvRecommendation } from "./uv-recommendation";
import "./uv.css";

export const metadata: Metadata = { title: "คำแนะนำ — Aphrodize" };

export default function Page() {
  return (
    <WorkspaceShell active="none" eyebrow="PERSONAL GUIDANCE" title="คำแนะนำ">
      <section className="page-content workspace-panel">
        <p className="eyebrow">คำแนะนำตามข้อมูลของคุณ</p>
        <h2>หมวดผลิตภัณฑ์ที่อาจตรงกับข้อมูลที่รายงาน</h2>
        <p>แสดงเฉพาะข้อมูลจากกฎที่ตรวจสอบย้อนกลับได้ คะแนนริ้วรอยจะใช้เมื่อผ่านเกณฑ์ที่เผยแพร่แล้วเท่านั้น</p>
        <RecommendationPanel />
        <div className="page-actions">
          <Link className="secondary-button" href="/result-detail">กลับผลรายบริเวณ</Link>
          <Link className="primary-button" href="/capture">ถ่ายภาพครั้งถัดไป →</Link>
        </div>
      </section>
      <UvRecommendation />
    </WorkspaceShell>
  );
}
