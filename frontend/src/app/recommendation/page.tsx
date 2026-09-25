import type { Metadata } from "next";
import Link from "next/link";
import { WorkspaceShell } from "@/components/workspace-shell";

export const metadata: Metadata = { title: "คำแนะนำ — Aphrodize" };

export default function Page() {
  return (
    <WorkspaceShell active="none" eyebrow="PERSONAL GUIDANCE" title="คำแนะนำ">
      <section className="page-content workspace-panel">
        <p className="eyebrow">คำแนะนำจากกฎ</p>
        <h2>คำแนะนำที่ผ่าน safety check</h2>
        <p>คำแนะนำนี้เป็นข้อมูลประกอบ ไม่ใช่การรักษาหรือการยืนยันสาเหตุ</p>
        <article className="recommendation-card">
          <span className="status moderate">ข้อมูลประกอบ</span>
          <h3>ดูแลเกราะป้องกันผิวและป้องกันแดด</h3>
          <p>หมวดผลิตภัณฑ์: moisturizer และ broad-spectrum sunscreen SPF 30+</p>
          <div className="rule-box">
            <h3>เหตุผลและแหล่งข้อมูล</h3>
            <p>ผลภาพ: periocular wrinkle score ผ่าน confidence threshold</p>
            <p>คุณรายงาน: ผิวแห้ง, UV exposure สูง และใช้ sunscreen ไม่สม่ำเสมอ</p>
            <p className="metadata">Rule R-UV-001 · version 1.0 · ไม่ยืนยันว่า UV เป็นสาเหตุ</p>
          </div>
        </article>
        <div className="page-actions"><Link className="secondary-button" href="/result-detail">กลับผลรายบริเวณ</Link><Link className="primary-button" href="/capture">ถ่ายภาพครั้งถัดไป →</Link></div>
      </section>
    </WorkspaceShell>
  );
}
