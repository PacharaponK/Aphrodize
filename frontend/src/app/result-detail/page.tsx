/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "ผลรายบริเวณ — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a className="active" href="/">ภาพรวม</a><a href="/capture">วิเคราะห์ภาพ</a><a href="/trend">แนวโน้ม</a></nav></header><section className="page-content"><p className="eyebrow">ตรวจพบจากภาพ</p><h1>ผลรายบริเวณ</h1><p>Wrinkle score เป็นค่าจากโมเดลเพื่อการติดตาม ไม่ใช่คะแนนสุขภาพหรือความงาม</p><div className="detail-grid"><div className="overlay-card">Wrinkle mask overlay preview</div><div className="data-list"><div><strong>รอบดวงตา</strong><span>ปานกลาง<br />confidence 0.86</span></div><div><strong>หน้าผาก</strong><span>เล็กน้อย<br />confidence 0.79</span></div><div><strong>ร่องแก้ม</strong><span>ปานกลาง<br />confidence 0.82</span></div></div></div><p className="metadata">Model v0.1 · score version mask-area-v1 · ภาพผ่าน quality gate</p><div className="page-actions"><a className="primary-button" href="/recommendation">ดูคำแนะนำจากกฎ →</a><a className="secondary-button" href="/">กลับหน้าภาพรวม</a></div></section></main></div>
    </>
  );
}



