"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";

export default function LoginPage() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      setMessage("กรอกอีเมลที่ถูกต้องและรหัสผ่านอย่างน้อย 8 ตัวอักษร");
      form.reportValidity();
      return;
    }
    const data = new FormData(form);
    setSubmitting(true);
    setMessage("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setMessage(body?.detail ?? "เข้าสู่ระบบไม่สำเร็จ");
        return;
      }
      router.push("/");
    } catch {
      setMessage("เชื่อมต่อบริการไม่ได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page"><ThemeToggle className="auth-theme-toggle" /><main className="auth-shell">
      <section className="auth-intro" aria-label="เกี่ยวกับ Aphrodize"><Link className="auth-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-logo.svg" alt="" unoptimized />Aphrodize</Link><div className="intro-copy"><p className="eyebrow">WELLNESS SKIN TRACKING</p><h1>ติดตามผิว<br /><span>อย่างอ่อนโยน</span></h1><p>เปรียบเทียบลักษณะผิวจากภาพภายใต้ protocol เดิม พร้อมแยกสิ่งที่ตรวจจากภาพออกจากข้อมูลที่คุณรายงาน</p></div><div className="intro-points"><span>✓ ไม่ใช่การวินิจฉัยโรค</span><span>✓ ขอความยินยอมก่อนวิเคราะห์ภาพ</span></div></section>
      <section className="auth-card" aria-labelledby="login-title"><div className="auth-card-heading"><p className="eyebrow">WELCOME BACK</p><h2 id="login-title">เข้าสู่ระบบ</h2><p>เข้าสู่ระบบเพื่อดูผลวิเคราะห์ของคุณ</p></div><form onSubmit={submit} noValidate aria-describedby="login-message"><label htmlFor="email">อีเมล</label><input id="email" name="email" type="email" autoComplete="email" placeholder="name@example.com" required disabled={submitting} /><label htmlFor="password">รหัสผ่าน</label><input id="password" name="password" type="password" autoComplete="current-password" placeholder="อย่างน้อย 8 ตัวอักษร" minLength={8} required disabled={submitting} /><p id="login-message" className="form-message" role="status" aria-live="polite">{message}</p><button className="primary-button auth-submit" type="submit" disabled={submitting}>{submitting ? "กำลังเข้าสู่ระบบ…" : <>เข้าสู่ระบบ <span>→</span></>}</button></form><p className="signup-link">ยังไม่มีบัญชี? <Link href="/signup">สร้างบัญชี</Link></p><p className="auth-privacy">ระบบจะขอความยินยอมก่อนวิเคราะห์ภาพใบหน้าของคุณ</p><Link className="auth-back" href="/">← กลับหน้าภาพรวม</Link></section>
    </main></div>
  );
}
