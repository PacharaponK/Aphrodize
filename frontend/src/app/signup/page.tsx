"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type SubmissionState = "idle" | "error" | "success";

export default function SignupPage() {
  const [message, setMessage] = useState("");
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionState, setSubmissionState] = useState<SubmissionState>("idle");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const password = String(data.get("password") ?? "");
    const confirmPassword = String(data.get("confirmPassword") ?? "");

    if (!form.checkValidity()) {
      setMessage("กรุณากรอกข้อมูลให้ครบถ้วน และใช้รหัสผ่านอย่างน้อย 8 ตัวอักษร");
      setSubmissionState("error");
      form.reportValidity();
      return;
    }
    if (password !== confirmPassword) {
      setMessage("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน");
      setSubmissionState("error");
      return;
    }

    setIsSubmitting(true);
    setMessage("");
    setSubmissionState("idle");
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: String(data.get("name") ?? "").trim(),
          email: String(data.get("email") ?? "").trim(),
          password,
          consent_accepted: data.get("consent") === "on",
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setMessage(body?.detail ?? "สร้างบัญชีไม่สำเร็จ โปรดลองอีกครั้ง");
        setSubmissionState("error");
        return;
      }
      setMessage("สร้างบัญชีสำเร็จแล้ว กำลังพาไปตอบแบบสอบถามสุขภาพครั้งแรก…");
      setSubmissionState("success");
      form.reset();
      router.push("/onboarding/health");
    } catch {
      setMessage("เชื่อมต่อบริการไม่ได้ กรุณาลองใหม่อีกครั้ง");
      setSubmissionState("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <main className="auth-shell">
        <section className="auth-intro" aria-label="เกี่ยวกับ Aphrodize">
          <Link className="auth-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</Link>
          <div className="intro-copy">
            <p className="eyebrow">WELLNESS SKIN TRACKING</p>
            <h1>เริ่มดูแลผิว<br /><span>ในแบบของคุณ</span></h1>
            <p>บันทึกและติดตามลักษณะผิวจากภาพ ภายใต้การตั้งค่าเดียวกัน เพื่อช่วยให้คุณเห็นการเปลี่ยนแปลงได้ชัดเจนขึ้น</p>
          </div>
          <div className="intro-points"><span>✓ ไม่ใช่การวินิจฉัยโรค</span><span>✓ คุณควบคุมข้อมูลและความยินยอมได้</span></div>
        </section>
        <section className="auth-card" aria-labelledby="signup-title">
          <div className="auth-card-heading"><p className="eyebrow">CREATE ACCOUNT</p><h2 id="signup-title">สร้างบัญชี</h2><p>เริ่มบันทึกและติดตามผลการดูแลผิวของคุณ</p></div>
          <form noValidate onSubmit={handleSubmit} aria-describedby="signup-message">
            <label htmlFor="name">ชื่อที่แสดง</label>
            <input id="name" name="name" type="text" autoComplete="name" placeholder="ชื่อของคุณ" minLength={1} maxLength={120} required disabled={isSubmitting} />
            <label htmlFor="email">อีเมล</label>
            <input id="email" name="email" type="email" autoComplete="email" placeholder="name@example.com" maxLength={320} required disabled={isSubmitting} />
            <label htmlFor="password">รหัสผ่าน</label>
            <input id="password" name="password" type="password" autoComplete="new-password" placeholder="อย่างน้อย 8 ตัวอักษร" minLength={8} maxLength={128} required disabled={isSubmitting} />
            <label htmlFor="confirm-password">ยืนยันรหัสผ่าน</label>
            <input id="confirm-password" name="confirmPassword" type="password" autoComplete="new-password" placeholder="กรอกรหัสผ่านอีกครั้ง" minLength={8} maxLength={128} required disabled={isSubmitting} />
            <label className="checkbox signup-consent"><input type="checkbox" name="consent" required disabled={isSubmitting} /> <span>ฉันยอมรับการจัดเก็บข้อมูลตามความยินยอมก่อนวิเคราะห์ภาพ</span></label>
            <p id="signup-message" className={`form-message ${submissionState}`} role="status" aria-live="polite">{message}</p>
            <button className="primary-button auth-submit" type="submit" disabled={isSubmitting}>{isSubmitting ? "กำลังสร้างบัญชี…" : <>สร้างบัญชี <span>→</span></>}</button>
          </form>
          <p className="signup-link">มีบัญชีอยู่แล้ว? <Link href="/login">เข้าสู่ระบบ</Link></p>
          <Link className="auth-back" href="/">← กลับหน้าภาพรวม</Link>
        </section>
      </main>
    </div>
  );
}
