"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";

type SubmissionState = "idle" | "error";
type AccountDetails = { displayName: string; email: string; password: string };
type AnswerMap = Record<string, string>;

const questions = [
  ["sex", "เพศ"], ["age_group", "ช่วงอายุของคุณ"], ["sleep_hours", "โดยเฉลี่ยเมื่อคืนคุณนอนกี่ชั่วโมง?"], ["sleep_quality", "คุณภาพการนอนของคุณเป็นอย่างไร?"], ["water_liters", "เมื่อวานคุณดื่มน้ำเปล่าประมาณกี่ลิตร?"], ["outdoor_minutes", "เมื่อวานคุณทำกิจกรรมกลางแจ้งกี่นาที?"], ["sunscreen_frequency", "คุณทาครีมกันแดดบ่อยแค่ไหน?"], ["skin_type", "คุณคิดว่าผิวหน้าของคุณเป็นประเภทใด?"], ["skin_sensitivity", "ผิวของคุณไวต่อการระคายเคืองเพียงใด?"], ["known_product_allergy", "คุณมีประวัติแพ้ผลิตภัณฑ์ดูแลผิวหรือไม่?"], ["severe_irritation", "ขณะนี้มีการระคายเคืองผิวอย่างรุนแรงหรือไม่?"], ["stress_level", "ระดับความเครียดในช่วงสัปดาห์นี้ (1 ต่ำ – 5 สูง)"], ["menstrual_tracking", "คุณต้องการติดตามข้อมูลรอบเดือนหรือไม่?"], ["menstrual_status", "วันนี้คุณอยู่ระหว่างมีประจำเดือนหรือไม่?"], ["wellness_goal", "เป้าหมายหลักที่อยากติดตามคืออะไร?"],
] as const;

const options: Record<string, readonly [string, string][]> = {
  sex: [["male", "ชาย"], ["female", "หญิง"], ["prefer_not_to_say", "ไม่สะดวกระบุ"]],
  age_group: [["under_13", "ต่ำกว่า 13 ปี"], ["13_17", "13–17 ปี"], ["18_24", "18–24 ปี"], ["25_34", "25–34 ปี"], ["35_44", "35–44 ปี"], ["45_54", "45–54 ปี"], ["55_plus", "55 ปีขึ้นไป"]],
  sleep_hours: [["4", "น้อยกว่า 5 ชั่วโมง"], ["5.5", "5–6 ชั่วโมง"], ["6.5", "6–7 ชั่วโมง"], ["7.5", "7–8 ชั่วโมง"], ["8.5", "8–9 ชั่วโมง"], ["9.5", "มากกว่า 9 ชั่วโมง"]],
  sleep_quality: [["poor", "ไม่ดี"], ["fair", "พอใช้"], ["good", "ดี"], ["excellent", "ดีมาก"]],
  water_liters: [["0.5", "น้อยกว่า 1 ลิตร"], ["1", "ประมาณ 1 ลิตร"], ["1.5", "ประมาณ 1.5 ลิตร"], ["2", "ประมาณ 2 ลิตร"], ["2.5", "ประมาณ 2.5 ลิตร"], ["3", "3 ลิตรขึ้นไป"]],
  outdoor_minutes: [["0", "ไม่ได้ทำกิจกรรมกลางแจ้ง"], ["15", "1–30 นาที"], ["45", "31–60 นาที"], ["90", "1–2 ชั่วโมง"], ["150", "มากกว่า 2 ชั่วโมง"]],
  sunscreen_frequency: [["never", "ไม่เคย"], ["sometimes", "บางครั้ง"], ["most_days", "เกือบทุกวัน"], ["every_day", "ทุกวัน"]],
  skin_type: [["dry", "แห้ง"], ["normal", "ปกติ"], ["combination", "ผสม"], ["oily", "มัน"], ["unsure", "ไม่แน่ใจ"]],
  skin_sensitivity: [["low", "ต่ำ"], ["medium", "ปานกลาง"], ["high", "สูง"], ["unsure", "ไม่แน่ใจ"]],
  known_product_allergy: [["no", "ไม่มีประวัติที่ทราบ"], ["yes", "มี"], ["unsure", "ไม่แน่ใจ"]],
  severe_irritation: [["no", "ไม่มี"], ["yes", "มี"], ["unsure", "ไม่แน่ใจ"]],
  stress_level: [["1", "1 — ต่ำมาก"], ["2", "2"], ["3", "3 — ปานกลาง"], ["4", "4"], ["5", "5 — สูงมาก"]],
  menstrual_tracking: [["yes", "ต้องการ"], ["no", "ไม่ต้องการ"], ["prefer_not_to_say", "ไม่สะดวกตอบ"], ["not_applicable", "ไม่เกี่ยวข้องกับฉัน"]],
  menstrual_status: [["on_period", "อยู่ระหว่างมีประจำเดือน"], ["not_on_period", "ไม่ได้อยู่ระหว่างมีประจำเดือน"], ["unsure", "ไม่แน่ใจ"], ["prefer_not_to_say", "ไม่สะดวกตอบ"]],
  wellness_goal: [["skin_tracking", "ติดตามผิว"], ["sleep", "การนอน"], ["hydration", "การดื่มน้ำ"], ["outdoor_habits", "กิจกรรมกลางแจ้ง"], ["general_wellness", "สุขภาพโดยรวม"]],
};

function wellnessPayload(answers: AnswerMap, guardianConsent: boolean) {
  return { sex: answers.sex, age_group: answers.age_group, guardian_consent: guardianConsent, sleep_hours: Number(answers.sleep_hours), sleep_quality: answers.sleep_quality, water_liters: Number(answers.water_liters), outdoor_minutes: Number(answers.outdoor_minutes), sunscreen_frequency: answers.sunscreen_frequency, skin_type: answers.skin_type, skin_sensitivity: answers.skin_sensitivity, known_product_allergy: answers.known_product_allergy, severe_irritation: answers.severe_irritation, stress_level: Number(answers.stress_level), menstrual_tracking: answers.sex === "male" ? "not_applicable" : answers.menstrual_tracking, menstrual_status: answers.sex === "male" ? "not_applicable" : answers.menstrual_status, wellness_goal: answers.wellness_goal };
}

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<"account" | "questions">("account");
  const [account, setAccount] = useState<AccountDetails | null>(null);
  const [message, setMessage] = useState("");
  const [submissionState, setSubmissionState] = useState<SubmissionState>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [accountCreated, setAccountCreated] = useState(false);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [guardianConsent, setGuardianConsent] = useState(false);
  const [questionIndex, setQuestionIndex] = useState(0);
  const visibleQuestions = useMemo(() => questions.filter(([name]) => answers.sex !== "male" || (name !== "menstrual_tracking" && name !== "menstrual_status")), [answers.sex]);
  const [questionName, questionLabel] = visibleQuestions[questionIndex];
  const isLastQuestion = questionIndex === visibleQuestions.length - 1;

  function clearMessage() { setMessage(""); setSubmissionState("idle"); }

  function confirmAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const password = String(data.get("password") ?? "");
    if (!form.checkValidity()) { setMessage("กรุณากรอกข้อมูลให้ครบถ้วน"); setSubmissionState("error"); form.reportValidity(); return; }
    if (password !== String(data.get("confirmPassword") ?? "")) { setMessage("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน"); setSubmissionState("error"); return; }
    setAccount({ displayName: String(data.get("name") ?? "").trim(), email: String(data.get("email") ?? "").trim(), password });
    clearMessage();
    setStep("questions");
  }

  function goNext() {
    if (!answers[questionName]) { setMessage("กรุณาเลือกคำตอบก่อนดำเนินการต่อ"); setSubmissionState("error"); return; }
    if (questionName === "age_group" && answers.age_group === "under_13" && !guardianConsent) { setMessage("กรุณายืนยันความยินยอมของผู้ปกครอง"); setSubmissionState("error"); return; }
    setQuestionIndex((current) => current + 1);
    clearMessage();
  }

  async function submitQuestions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!account || visibleQuestions.some(([name]) => !answers[name])) { setMessage("กรุณาตอบคำถามให้ครบถ้วน"); setSubmissionState("error"); return; }
    setIsSubmitting(true); clearMessage();
    try {
      if (!accountCreated) {
        const signup = await fetch("/api/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ display_name: account.displayName, email: account.email, password: account.password, consent_accepted: true }) });
        const body = await signup.json().catch(() => null);
        if (!signup.ok) { setMessage(body?.detail ?? "สร้างบัญชีไม่สำเร็จ โปรดลองอีกครั้ง"); setSubmissionState("error"); return; }
        setAccountCreated(true);
      }
      const questionnaire = await fetch("/api/onboarding/health", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(wellnessPayload(answers, guardianConsent)) });
      const body = await questionnaire.json().catch(() => null);
      if (!questionnaire.ok) { setMessage(body?.detail ?? "บัญชีถูกสร้างแล้ว แต่บันทึกข้อมูลสุขภาพไม่สำเร็จ กรุณาลองอีกครั้ง"); setSubmissionState("error"); return; }
      router.push("/");
    } catch {
      setMessage(accountCreated ? "บัญชีถูกสร้างแล้ว แต่เชื่อมต่อเพื่อบันทึกข้อมูลสุขภาพไม่ได้ กรุณาลองอีกครั้ง" : "เชื่อมต่อบริการไม่ได้ กรุณาลองใหม่อีกครั้ง"); setSubmissionState("error");
    } finally { setIsSubmitting(false); }
  }

  return <div className="auth-page"><ThemeToggle className="auth-theme-toggle" /><main className="auth-shell">
    <section className="auth-intro" aria-label="เกี่ยวกับ Aphrodize"><Link className="auth-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-logo.svg" alt="" unoptimized />Aphrodize</Link><div className="intro-copy"><p className="eyebrow">WELLNESS SKIN TRACKING</p><h1>เริ่มดูแลผิว<br /><span>ในแบบของคุณ</span></h1><p>สร้างบัญชีและตอบคำถามสุขภาพอย่างเป็นขั้นตอน เพื่อเริ่มติดตามผิวได้ทันที</p></div><div className="intro-points"><span>✓ ไม่ใช่การวินิจฉัยโรค</span><span>✓ คุณควบคุมข้อมูลและความยินยอมได้</span></div></section>
    <section className="auth-card signup-card" aria-labelledby="signup-title"><div className="auth-card-heading"><p className="eyebrow">CREATE ACCOUNT · FIRST-TIME SETUP</p><h2 id="signup-title">{step === "account" ? "สร้างบัญชี" : "ข้อมูลสุขภาพเบื้องต้น"}</h2><p>{step === "account" ? "ยืนยันข้อมูลบัญชีของคุณก่อนเริ่มตอบคำถาม" : "ตอบคำถามทีละข้อ ข้อมูลนี้ใช้สำหรับการติดตามส่วนบุคคล"}</p></div>
      {step === "account" ? <form noValidate onSubmit={confirmAccount} aria-describedby="signup-message"><fieldset className="signup-section"><legend>ข้อมูลบัญชี</legend><label htmlFor="name">ชื่อที่แสดง</label><input id="name" name="name" type="text" autoComplete="name" placeholder="ชื่อของคุณ" minLength={1} maxLength={120} required /><label htmlFor="email">อีเมล</label><input id="email" name="email" type="email" autoComplete="email" placeholder="name@example.com" maxLength={320} required /><label htmlFor="password">รหัสผ่าน</label><input id="password" name="password" type="password" autoComplete="new-password" placeholder="อย่างน้อย 8 ตัวอักษร" minLength={8} maxLength={128} required /><label htmlFor="confirm-password">ยืนยันรหัสผ่าน</label><input id="confirm-password" name="confirmPassword" type="password" autoComplete="new-password" placeholder="กรอกรหัสผ่านอีกครั้ง" minLength={8} maxLength={128} required /><label className="checkbox signup-consent"><input type="checkbox" name="consent" required /> <span>ฉันยอมรับการจัดเก็บข้อมูลตามความยินยอมก่อนวิเคราะห์ภาพ</span></label></fieldset><p id="signup-message" className={`form-message ${submissionState}`} role="status" aria-live="polite">{message}</p><button className="primary-button auth-submit" type="submit">ยืนยันและไปต่อ →</button></form> : <form noValidate onSubmit={submitQuestions} aria-describedby="signup-message"><fieldset className="signup-section signup-wizard"><legend>คำถามสุขภาพ</legend><div className="wizard-progress" aria-label={`คำถาม ${questionIndex + 1} จาก ${visibleQuestions.length}`}><span>คำถาม {questionIndex + 1} / {visibleQuestions.length}</span><div aria-hidden="true"><i style={{ width: `${((questionIndex + 1) / visibleQuestions.length) * 100}%` }} /></div></div><div className="wizard-question"><label htmlFor={questionName}>{questionIndex + 1}. {questionLabel}</label><select id={questionName} value={answers[questionName] ?? ""} onChange={(item) => { setAnswers((current) => ({ ...current, [questionName]: item.target.value })); clearMessage(); }} disabled={isSubmitting} required><option value="" disabled>เลือกคำตอบ</option>{options[questionName].map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select>{questionName === "age_group" && answers.age_group === "under_13" && <label className="onboarding-guardian"><input type="checkbox" checked={guardianConsent} onChange={(item) => setGuardianConsent(item.target.checked)} disabled={isSubmitting} /> <span>ฉันเป็นผู้ปกครองตามกฎหมายและยินยอมให้เก็บข้อมูลนี้เพื่อการติดตามสุขภาพ</span></label>}</div><div className="wizard-actions"><button type="button" className="secondary-button" onClick={() => setQuestionIndex((current) => current - 1)} disabled={questionIndex === 0 || isSubmitting}>← ก่อนหน้า</button>{isLastQuestion ? <button className="primary-button" type="submit" disabled={isSubmitting}>{isSubmitting ? "กำลังบันทึกข้อมูล…" : accountCreated ? "บันทึกข้อมูลสุขภาพอีกครั้ง" : "สร้างบัญชีและเริ่มใช้งาน →"}</button> : <button type="button" className="primary-button" onClick={goNext} disabled={isSubmitting}>ถัดไป →</button>}</div></fieldset><p id="signup-message" className={`form-message ${submissionState}`} role="status" aria-live="polite">{message}</p></form>}
      <p className="signup-link">มีบัญชีอยู่แล้ว? <Link href="/login">เข้าสู่ระบบ</Link></p><Link className="auth-back" href="/">← กลับหน้าภาพรวม</Link>
    </section>
  </main></div>;
}
