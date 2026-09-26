import type { Metadata } from "next";
import Image from "next/image";
import Script from "next/script";

export const metadata: Metadata = { title: "Aphrodize — Skin tracking" };

export default function Page() {
  return (
    <>
      
<div className="app-shell">
<aside className="sidebar" aria-label="เมนูหลัก">
<a className="brand" href="#dashboard" aria-label="Aphrodize home"><Image width={40} height={40} className="brand-mark" src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a>
<nav>
<a className="nav-link active" href="#dashboard">ภาพรวม</a>
<a className="nav-link" href="/capture">วิเคราะห์ภาพ</a>
<a className="nav-link" href="/clients">สุขภาพรายวัน</a>
<a className="nav-link" href="#trend">แนวโน้ม</a>
<a className="nav-link" href="#profile">Skin profile</a>
</nav>
<div className="privacy-card"><strong>ข้อมูลของคุณ</strong><span>เก็บตาม consent ที่คุณเลือก</span><a href="#privacy">จัดการข้อมูล</a></div>
</aside>
<main id="dashboard">
<header className="topbar"><div><p className="eyebrow">ภาพล่าสุด · 20 ก.ย. 2026</p><h1>สวัสดี, Ink</h1></div><button className="avatar" aria-label="เปิดโปรไฟล์">I</button></header>
<section className="notice" aria-label="ข้อจำกัดของผลลัพธ์"><span>i</span><p>แดชบอร์ดหน้านี้ยังเป็นข้อมูลตัวอย่าง หากต้องการผลจากภาพจริงให้ไปที่ <a href="/capture">วิเคราะห์ภาพ</a> คะแนนทดลองยังไม่ผ่านการตรวจสอบและไม่ใช่การวินิจฉัย</p></section>
<section className="hero-grid" aria-label="สรุปผลล่าสุด">
<article className="score-card"><p className="eyebrow">ตัวอย่าง UI · WRINKLE SCORE</p><div className="score-line"><strong>37</strong><span>/ 100</span></div><p className="status moderate">ปานกลาง</p><p className="metadata">ตัวเลขตัวอย่าง ไม่ใช่ผลวิเคราะห์ของคุณ</p><a className="text-button" href="/result-detail">ดูผลล่าสุด <span>→</span></a></article>
<article className="capture-card" id="capture"><div><p className="eyebrow">เริ่มวิเคราะห์</p><h2>พร้อมบันทึกภาพใหม่ไหม?</h2><p>หน้าสด · หน้าตรง · แสงกระจาย เพื่อให้เทียบผลได้ดีขึ้น</p></div><a className="primary-button" href="/capture">ถ่ายภาพใหม่ <span>→</span></a></article>
</section>
<section className="section-heading" id="trend"><div><p className="eyebrow">HISTORY</p><h2>แนวโน้มของคุณ</h2></div><button className="text-button" data-open="trend-detail">ดูทั้งหมด →</button></section>
<article className="trend-card"><div className="trend-info"><span className="trend-icon">⌁</span><div><h3>เริ่มติดตามแนวโน้มได้แล้ว</h3><p>มีภาพที่ผ่าน quality gate 1 ครั้ง อีก 1 ครั้งจะแสดงแนวโน้มเปรียบเทียบให้</p></div></div><div className="chart" aria-label="ตัวอย่างกราฟแนวโน้ม"><span>สัปดาห์ 1</span><i></i><i></i><i></i><span>สัปดาห์ 12</span></div></article>
<section className="section-heading"><div><p className="eyebrow">LATEST ANALYSIS</p><h2>สิ่งที่ตรวจพบจากภาพ</h2></div><button className="text-button" data-open="details">ดูรายละเอียด →</button></section>
<section className="result-grid"><article className="result-card"><span className="result-icon purple">◌</span><div><p className="eyebrow">รอบดวงตา</p><h3>ปานกลาง</h3><p className="metadata">confidence 0.86</p></div></article><article className="result-card"><span className="result-icon blue">⌁</span><div><p className="eyebrow">หน้าผาก</p><h3>เล็กน้อย</h3><p className="metadata">confidence 0.79</p></div></article><article className="result-card"><span className="result-icon green">✓</span><div><p className="eyebrow">คุณภาพภาพ</p><h3>ผ่าน</h3><p className="metadata">ใช้ในแนวโน้มได้</p></div></article></section>
<section className="sources-grid" id="profile"><article><p className="eyebrow">คุณรายงาน</p><h2>ผิวแห้ง · ระคายง่าย</h2><p>UV exposure สูง · ใช้ sunscreen ไม่สม่ำเสมอ</p><button className="text-button">แก้ไขข้อมูล →</button></article><article><p className="eyebrow">คำแนะนำจากกฎ</p><h2>ดูแลเกราะป้องกันผิว</h2><p>แสดงจากข้อมูลที่คุณรายงานร่วมกับผลภาพที่ confidence ผ่านเกณฑ์</p><button className="text-button" data-open="recommendation">ดูเหตุผลและ safety check →</button></article></section>
</main>
</div>
<nav className="mobile-nav" aria-label="เมนูมือถือ"><a className="active" href="#dashboard">⌂<span>ภาพรวม</span></a><a href="/capture">＋<span>วิเคราะห์</span></a><a href="/clients">◉<span>สุขภาพ</span></a><a href="#profile">☷<span>โปรไฟล์</span></a></nav>
<dialog id="capture-panel"><button className="close-button" data-close aria-label="ปิด">×</button><p className="eyebrow">ก่อนวิเคราะห์</p><h2>ถ่ายภาพให้เทียบกันได้</h2><div className="face-guide"><div className="face-shape">◡</div><p>หน้าสด · หน้าตรง · แสงกระจาย</p></div><ul className="checklist"><li>ไม่ใช้ beauty filter และไม่แต่งหน้าหนัก</li><li>สีหน้าเป็นกลาง และภาพไม่เบลอ</li><li>ใช้ระยะและแสงใกล้เคียงครั้งก่อน</li></ul><button className="primary-button" data-open="quality-panel">เปิดกล้อง / เลือกภาพ →</button><p className="metadata">Consent version 1.0 · <a href="#privacy">ดูหรือถอน consent</a></p></dialog>
<dialog id="quality-panel"><button className="close-button" data-close aria-label="ปิด">×</button><div className="warning-icon">!</div><p className="eyebrow">QUALITY GATE</p><h2>ภาพนี้ยังใช้เปรียบเทียบไม่ได้</h2><p>จึงไม่นำไปคำนวณผลหรือแนวโน้ม</p><ul className="warning-list"><li>แสงน้อยเกินไป</li><li>ภาพอาจเบลอ</li></ul><p className="metadata">ลองหันหน้าเข้าหาแสงที่นุ่มและวางกล้องให้นิ่ง</p><button className="primary-button" data-open="capture-panel">ถ่ายภาพใหม่ →</button></dialog>
<dialog id="details"><button className="close-button" data-close aria-label="ปิด">×</button><p className="eyebrow">ตรวจพบจากภาพ</p><h2>ผลรายบริเวณ</h2><div className="mask-preview"><span>Wrinkle mask overlay</span></div><dl><div><dt>รอบดวงตา</dt><dd>ปานกลาง · confidence 0.86</dd></div><div><dt>หน้าผาก</dt><dd>เล็กน้อย · confidence 0.79</dd></div><div><dt>ร่องแก้ม</dt><dd>ปานกลาง · confidence 0.82</dd></div></dl><p className="metadata">Model version: v0.1 · score version: mask-area-v1</p></dialog>
<dialog id="trend-detail"><button className="close-button" data-close aria-label="ปิด">×</button><p className="eyebrow">HISTORY</p><h2>แนวโน้มของคุณ</h2><div className="mask-preview"><span>Trend visualization จะพร้อมเมื่อมีภาพผ่านอย่างน้อย 2 ครั้ง</span></div><p>ภาพล่าสุดผ่าน quality gate แล้ว อีก 1 ภาพที่ถ่ายภายใต้ protocol เดิมจะช่วยให้เปรียบเทียบได้</p><button className="primary-button" data-open="capture-panel">ถ่ายภาพครั้งถัดไป →</button></dialog>
<dialog id="recommendation"><button className="close-button" data-close aria-label="ปิด">×</button><p className="eyebrow">คำแนะนำจากกฎ</p><h2>ดูแลเกราะป้องกันผิวและป้องกันแดด</h2><p>หมวดผลิตภัณฑ์: moisturizer และ broad-spectrum sunscreen SPF 30+</p><hr /><h3>เหตุผลและแหล่งข้อมูล</h3><p>ผลภาพ: periocular wrinkle score ผ่าน confidence threshold</p><p>คุณรายงาน: ผิวแห้ง, UV exposure สูง และใช้ sunscreen ไม่สม่ำเสมอ</p><p className="metadata">Rule R-UV-001 · v1.0 · ไม่ยืนยันว่า UV เป็นสาเหตุ</p></dialog>



      <Script src="/legacy/home.js" strategy="afterInteractive" />
    </>
  );
}



