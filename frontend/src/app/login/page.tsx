"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle, useLanguage } from "@/components/language-provider";

export default function LoginPage() {
  const router = useRouter();
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      setMessage(t("กรอกอีเมลที่ถูกต้องและรหัสผ่านอย่างน้อย 8 ตัวอักษร", "Enter a valid email and a password with at least 8 characters."));
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
        setMessage(body?.detail ?? t("เข้าสู่ระบบไม่สำเร็จ", "Could not sign in. Check your details and try again."));
        return;
      }
      router.push("/");
    } catch {
      setMessage(t("เชื่อมต่อบริการไม่ได้ กรุณาลองใหม่อีกครั้ง", "Could not reach the service. Please try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page"><LanguageToggle className="auth-language-toggle" /><ThemeToggle className="auth-theme-toggle" /><main className="auth-shell">
      <section className="auth-intro" aria-label={t("เกี่ยวกับ Aphrodize", "About Aphrodize")}><Link className="auth-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-logo.svg" alt="" unoptimized />Aphrodize</Link><div className="intro-copy"><p className="eyebrow">WELLNESS SKIN TRACKING</p><h1>{t("ติดตามผิว", "Care for your skin")}<br /><span>{t("อย่างอ่อนโยน", "with confidence")}</span></h1><p>{t("เปรียบเทียบลักษณะผิวจากภาพภายใต้ protocol เดิม พร้อมแยกสิ่งที่ตรวจจากภาพออกจากข้อมูลที่คุณรายงาน", "Compare skin observations under consistent image conditions, while keeping image findings distinct from your self-reported information.")}</p></div><div className="intro-points"><span>✓ {t("ไม่ใช่การวินิจฉัยโรค", "Not a medical diagnosis")}</span><span>✓ {t("ขอความยินยอมก่อนวิเคราะห์ภาพ", "Your consent is required before image analysis")}</span></div></section>
      <section className="auth-card" aria-labelledby="login-title"><div className="auth-card-heading"><p className="eyebrow">WELCOME BACK</p><h2 id="login-title">{t("เข้าสู่ระบบ", "Sign in")}</h2><p>{t("เข้าสู่ระบบเพื่อดูผลวิเคราะห์ของคุณ", "Sign in to view your analysis results.")}</p></div><form onSubmit={submit} noValidate aria-describedby="login-message"><label htmlFor="email">{t("อีเมล", "Email")}</label><input id="email" name="email" type="email" autoComplete="email" placeholder="name@example.com" required disabled={submitting} /><label htmlFor="password">{t("รหัสผ่าน", "Password")}</label><input id="password" name="password" type="password" autoComplete="current-password" placeholder={t("อย่างน้อย 8 ตัวอักษร", "At least 8 characters")} minLength={8} required disabled={submitting} /><p id="login-message" className="form-message" role="status" aria-live="polite">{message}</p><button className="primary-button auth-submit" type="submit" disabled={submitting}>{submitting ? t("กำลังเข้าสู่ระบบ…", "Signing in…") : <>{t("เข้าสู่ระบบ", "Sign in")} <span>→</span></>}</button></form><p className="signup-link">{t("ยังไม่มีบัญชี?", "New to Aphrodize?")} <Link href="/signup">{t("สร้างบัญชี", "Create an account")}</Link></p><p className="auth-privacy">{t("ระบบจะขอความยินยอมก่อนวิเคราะห์ภาพใบหน้าของคุณ", "We will ask for your consent before analyzing your face image.")}</p><Link className="auth-back" href="/">{t("← กลับหน้าภาพรวม", "← Back to overview")}</Link></section>
    </main></div>
  );
}
