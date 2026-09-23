import type { Metadata } from "next";
import Image from "next/image";
import Script from "next/script";

export const metadata: Metadata = { title: "เข้าสู่ระบบ — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="auth-page">
<main className="auth-shell">
<section className="auth-intro" aria-label="เกี่ยวกับ Aphrodize">
<a className="auth-brand" href="/login"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a>
<div className="intro-copy"><p className="eyebrow">WELLNESS SKIN TRACKING</p><h1>ติดตามผิวของคุณ<br /><span>อย่างอ่อนโยน</span></h1><p>เปรียบเทียบลักษณะผิวจากภาพภายใต้ protocol เดิม พร้อมแยกสิ่งที่ตรวจจากภาพออกจากข้อมูลที่คุณรายงาน</p></div>
<div className="intro-points"><span>✓ ไม่ใช่การวินิจฉัยโรค</span><span>✓ คุณจัดการ consent และข้อมูลได้</span></div>
</section>
<section className="auth-card" aria-labelledby="login-title">
<div className="auth-card-heading"><p className="eyebrow">WELCOME BACK</p><h2 id="login-title">เข้าสู่ระบบ</h2><p>เข้าสู่ระบบเพื่อดูผลและแนวโน้มของคุณ</p></div>
<form id="login-form" noValidate>
<label htmlFor="email">อีเมล</label>
<input id="email" name="email" type="email" autoComplete="email" placeholder="name@example.com" required />
<label htmlFor="password">รหัสผ่าน</label>
<div className="password-field"><input id="password" name="password" type="password" autoComplete="current-password" placeholder="อย่างน้อย 8 ตัวอักษร" minLength={8} required /><button type="button" id="toggle-password" aria-label="แสดงรหัสผ่าน">แสดง</button></div>
<div className="form-row"><label className="checkbox"><input type="checkbox" name="remember" /> <span>จดจำการเข้าสู่ระบบ</span></label><a href="#reset">ลืมรหัสผ่าน?</a></div>
<p id="form-message" className="form-message" role="alert" aria-live="polite"></p>
<button className="primary-button auth-submit" type="submit">เข้าสู่ระบบ <span>→</span></button>
</form>
<p className="signup-link">ยังไม่มีบัญชี? <a href="#signup">สร้างบัญชี</a></p>
<p className="auth-privacy">การเข้าสู่ระบบหมายถึงคุณยอมรับ <a href="#privacy">Privacy notice</a> และจัดการ consent ได้ทุกเมื่อ</p>
</section>
</main>

</div>
      <Script src="/legacy/login.js" strategy="afterInteractive" />
    </>
  );
}




