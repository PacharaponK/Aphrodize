/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "Aphrodize — UI preview" };

export default function Page() {
  return (
    <>
      <div className="simple-page">
<main className="page-frame">
<header className="page-header"><a className="page-brand" href="/showcase"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a></header>
<section className="page-content">
<p className="eyebrow">UI FLOWS</p>
<h1>เลือกหน้าที่ต้องการดู</h1>
<p>ตัวอย่างหน้าจอทั้งหมดใน Next.js ยังใช้ข้อมูลตัวอย่างและไม่ได้เชื่อม API</p>
<div className="showcase-grid">
<a href="/login"><span>01</span><strong>Login</strong></a><a href="/"><span>02</span><strong>Dashboard</strong></a><a href="/capture"><span>03</span><strong>Capture guide</strong></a><a href="/quality-rejected"><span>04</span><strong>Quality rejected</strong></a><a href="/result-detail"><span>05</span><strong>Result detail</strong></a><a href="/trend"><span>06</span><strong>Trend</strong></a><a href="/recommendation"><span>07</span><strong>Recommendation</strong></a><a href="/profile"><span>08</span><strong>Skin profile</strong></a>
</div>
</section>
</main>
</div>
    </>
  );
}



