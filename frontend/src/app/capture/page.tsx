/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "วิเคราะห์ภาพ — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a href="/">ภาพรวม</a><a className="active" href="/capture">วิเคราะห์ภาพ</a><a href="/trend">แนวโน้ม</a></nav></header><section className="page-content"><p className="eyebrow">NEW ANALYSIS</p><h1>ถ่ายภาพให้เทียบกันได้</h1><p>รักษาระยะ มุม และแสงให้ใกล้เคียงภาพก่อนหน้า เพื่อให้ผลติดตามมีความหมาย</p><div className="step-row"><span className="step">1 · Consent</span><span className="step">2 · Skin profile</span><span className="step active">3 · Capture</span></div><div className="upload-box"><div><div className="upload-icon">⌁</div><h2>หน้าสด · หน้าตรง · แสงกระจาย</h2><p>ไม่ใช้ beauty filter · สีหน้าเป็นกลาง · ภาพไม่เบลอ</p></div></div><div className="page-actions"><a className="primary-button" href="/quality-rejected">เปิดกล้อง / เลือกภาพ →</a><a className="secondary-button" href="/">กลับหน้าภาพรวม</a></div><p className="metadata">Consent version 1.0 · คุณสามารถดูหรือถอน consent ได้จากการตั้งค่า</p></section></main></div>
    </>
  );
}



