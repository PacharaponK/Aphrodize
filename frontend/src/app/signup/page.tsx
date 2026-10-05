"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle, useLanguage } from "@/components/language-provider";
import { AuthIntroVideo } from "@/components/auth-intro-video";
import { AllergyIngredients } from "@/components/allergy-ingredients";
import { Select } from "@/components/ui/select";

type SubmissionState = "idle" | "error";
type AccountDetails = { displayName: string; email: string; password: string };
type AnswerMap = Record<string, string>;

const questions = [
  ["sex", "เพศ"], ["age_years", "อายุของคุณ (ปี)"], ["height_cm", "ส่วนสูงของคุณ (เซนติเมตร)"], ["weight_kg", "น้ำหนักของคุณ (กิโลกรัม)"], ["sleep_hours", "โดยเฉลี่ยเมื่อคืนคุณนอนกี่ชั่วโมง?"], ["sleep_quality", "คุณภาพการนอนของคุณเป็นอย่างไร?"], ["water_liters", "เมื่อวานคุณดื่มน้ำเปล่าประมาณกี่ลิตร?"], ["outdoor_minutes", "เมื่อวานคุณทำกิจกรรมกลางแจ้งกี่นาที?"], ["sunscreen_frequency", "คุณทาครีมกันแดดบ่อยแค่ไหน?"], ["skin_type", "คุณคิดว่าผิวหน้าของคุณเป็นประเภทใด?"], ["skin_sensitivity", "ผิวของคุณไวต่อการระคายเคืองเพียงใด?"], ["known_product_allergy", "คุณมีประวัติแพ้ผลิตภัณฑ์ดูแลผิวหรือไม่?"], ["allergy_details", "โปรดระบุส่วนผสมหรือผลิตภัณฑ์ที่เคยแพ้"], ["severe_irritation", "ขณะนี้มีการระคายเคืองผิวอย่างรุนแรงหรือไม่?"], ["stress_level", "ระดับความเครียดในช่วงสัปดาห์นี้ (1 ต่ำ – 5 สูง)"], ["menstrual_tracking", "คุณต้องการติดตามข้อมูลรอบเดือนหรือไม่?"], ["menstrual_status", "วันนี้คุณอยู่ระหว่างมีประจำเดือนหรือไม่?"], ["wellness_goal", "เป้าหมายหลักที่อยากติดตามคืออะไร?"],
] as const;

const options: Record<string, readonly [string, string][]> = {
  sex: [["male", "ชาย"], ["female", "หญิง"], ["prefer_not_to_say", "ไม่สะดวกระบุ"]],
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

const englishQuestions: Record<string, string> = {
  sex: "Gender", age_years: "What is your age in years?", height_cm: "What is your height in centimetres?", weight_kg: "What is your weight in kilograms?", sleep_hours: "On average, how many hours did you sleep last night?",
  sleep_quality: "How would you rate your sleep quality?", water_liters: "How much plain water did you drink yesterday?",
  outdoor_minutes: "How many minutes were you outdoors yesterday?", sunscreen_frequency: "How often do you use sunscreen?",
  skin_type: "Which skin type best describes your face?", skin_sensitivity: "How sensitive is your skin to irritation?",
  known_product_allergy: "Do you have a known skincare-product allergy?", allergy_details: "Which ingredient or product caused the reaction?", severe_irritation: "Are you currently experiencing severe skin irritation?",
  stress_level: "How stressed have you felt this week? (1 low – 5 high)", menstrual_tracking: "Would you like to track menstrual information?",
  menstrual_status: "Are you menstruating today?", wellness_goal: "What would you most like to track?",
};

const englishOptions: Record<string, Record<string, string>> = {
  sex: { male: "Male", female: "Female", prefer_not_to_say: "Prefer not to say" },
  age_group: { under_13: "Under 13", "13_17": "13–17 years", "18_24": "18–24 years", "25_34": "25–34 years", "35_44": "35–44 years", "45_54": "45–54 years", "55_plus": "55 years or older" },
  sleep_hours: { "4": "Under 5 hours", "5.5": "5–6 hours", "6.5": "6–7 hours", "7.5": "7–8 hours", "8.5": "8–9 hours", "9.5": "Over 9 hours" },
  sleep_quality: { poor: "Poor", fair: "Fair", good: "Good", excellent: "Excellent" },
  water_liters: { "0.5": "Under 1 liter", "1": "About 1 liter", "1.5": "About 1.5 liters", "2": "About 2 liters", "2.5": "About 2.5 liters", "3": "3 liters or more" },
  outdoor_minutes: { "0": "No outdoor activity", "15": "1–30 minutes", "45": "31–60 minutes", "90": "1–2 hours", "150": "Over 2 hours" },
  sunscreen_frequency: { never: "Never", sometimes: "Sometimes", most_days: "Most days", every_day: "Every day" },
  skin_type: { dry: "Dry", normal: "Normal", combination: "Combination", oily: "Oily", unsure: "Not sure" },
  skin_sensitivity: { low: "Low", medium: "Medium", high: "High", unsure: "Not sure" },
  known_product_allergy: { no: "No known allergy", yes: "Yes", unsure: "Not sure" },
  severe_irritation: { no: "No", yes: "Yes", unsure: "Not sure" },
  stress_level: { "1": "1 — Very low", "2": "2", "3": "3 — Moderate", "4": "4", "5": "5 — Very high" },
  menstrual_tracking: { yes: "Yes", no: "No", prefer_not_to_say: "Prefer not to answer", not_applicable: "Not applicable to me" },
  menstrual_status: { on_period: "Yes, I am menstruating", not_on_period: "No", unsure: "Not sure", prefer_not_to_say: "Prefer not to answer" },
  wellness_goal: { skin_tracking: "Skin tracking", sleep: "Sleep", hydration: "Hydration", outdoor_habits: "Outdoor activity", general_wellness: "General wellness" },
};

function ageGroupForAge(age: number): string {
  if (age < 13) return "under_13";
  if (age < 18) return "13_17";
  if (age < 25) return "18_24";
  if (age < 35) return "25_34";
  if (age < 45) return "35_44";
  if (age < 55) return "45_54";
  return "55_plus";
}

function wellnessPayload(answers: AnswerMap, guardianConsent: boolean, allergyIngredients: string[]) {
  const ageYears = Number(answers.age_years);
  return { allergy_ingredients: answers.known_product_allergy === "yes" ? allergyIngredients : [], sex: answers.sex, age_group: ageGroupForAge(ageYears), age_years: ageYears, guardian_consent: guardianConsent, height_cm: Number(answers.height_cm), weight_kg: Number(answers.weight_kg), sleep_hours: Number(answers.sleep_hours), sleep_quality: answers.sleep_quality, water_liters: Number(answers.water_liters), outdoor_minutes: Number(answers.outdoor_minutes), sunscreen_frequency: answers.sunscreen_frequency, skin_type: answers.skin_type, skin_sensitivity: answers.skin_sensitivity, known_product_allergy: answers.known_product_allergy, allergy_details: answers.known_product_allergy === "yes" ? answers.allergy_details : null, severe_irritation: answers.severe_irritation, stress_level: Number(answers.stress_level), menstrual_tracking: answers.sex === "male" ? "not_applicable" : answers.menstrual_tracking, menstrual_status: answers.sex === "male" ? "not_applicable" : answers.menstrual_status, wellness_goal: answers.wellness_goal };
}

export default function SignupPage() {
  const router = useRouter();
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [step, setStep] = useState<"account" | "questions">("account");
  const [account, setAccount] = useState<AccountDetails | null>(null);
  const [message, setMessage] = useState("");
  const [submissionState, setSubmissionState] = useState<SubmissionState>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [accountCreated, setAccountCreated] = useState(false);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [guardianConsent, setGuardianConsent] = useState(false);
  const [allergyIngredients, setAllergyIngredients] = useState<string[]>([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const visibleQuestions = useMemo(() => questions.filter(([name]) => (answers.sex !== "male" || (name !== "menstrual_tracking" && name !== "menstrual_status")) && (name !== "allergy_details" || answers.known_product_allergy === "yes")), [answers.sex, answers.known_product_allergy]);
  const [questionName, questionLabel] = visibleQuestions[questionIndex];
  const displayedQuestion = language === "en" ? englishQuestions[questionName] ?? questionLabel : questionLabel;
  const isLastQuestion = questionIndex === visibleQuestions.length - 1;

  function clearMessage() { setMessage(""); setSubmissionState("idle"); }

  function confirmAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const password = String(data.get("password") ?? "");
    if (!form.checkValidity()) { setMessage(t("กรุณากรอกข้อมูลให้ครบถ้วน", "Please complete all required fields.")); setSubmissionState("error"); form.reportValidity(); return; }
    if (password !== String(data.get("confirmPassword") ?? "")) { setMessage(t("รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน", "The passwords do not match.")); setSubmissionState("error"); return; }
    setAccount({ displayName: String(data.get("name") ?? "").trim(), email: String(data.get("email") ?? "").trim(), password });
    clearMessage();
    setStep("questions");
  }

  function goNext() {
    if (!answers[questionName] && !(questionName === "allergy_details" && allergyIngredients.length)) { setMessage(t("กรุณาเลือกคำตอบก่อนดำเนินการต่อ", "Choose an answer before continuing.")); setSubmissionState("error"); return; }
    if (questionName === "age_years" && Number(answers.age_years) < 13 && !guardianConsent) { setMessage(t("กรุณายืนยันความยินยอมของผู้ปกครอง", "Parent or guardian consent is required.")); setSubmissionState("error"); return; }
    setQuestionIndex((current) => current + 1);
    clearMessage();
  }

  async function submitQuestions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!account || visibleQuestions.some(([name]) => !answers[name] && !(name === "allergy_details" && allergyIngredients.length))) { setMessage(t("กรุณาตอบคำถามให้ครบถ้วน", "Please answer every required question.")); setSubmissionState("error"); return; }
    setIsSubmitting(true); clearMessage();
    try {
      if (!accountCreated) {
        const signup = await fetch("/api/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ display_name: account.displayName, email: account.email, password: account.password, consent_accepted: true }) });
        const body = await signup.json().catch(() => null);
        if (!signup.ok) { setMessage(body?.detail ?? "สร้างบัญชีไม่สำเร็จ โปรดลองอีกครั้ง"); setSubmissionState("error"); return; }
        setAccountCreated(true);
      }
      const questionnaire = await fetch("/api/onboarding/health", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(wellnessPayload(answers, guardianConsent, allergyIngredients)) });
      const body = await questionnaire.json().catch(() => null);
      if (!questionnaire.ok) { setMessage(body?.detail ?? "บัญชีถูกสร้างแล้ว แต่บันทึกข้อมูลสุขภาพไม่สำเร็จ กรุณาลองอีกครั้ง"); setSubmissionState("error"); return; }
      const measurements = await Promise.all([
        fetch("/api/daily-health/profile/height", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ consent_given: true, height_cm: Number(answers.height_cm) }) }),
        fetch("/api/daily-health/profile/weight", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ consent_given: true, weight_kg: Number(answers.weight_kg) }) }),
      ]);
      if (measurements.some((response) => !response.ok)) { setMessage(t("บัญชีและแบบสอบถามถูกบันทึกแล้ว แต่บันทึกส่วนสูงหรือน้ำหนักไม่สำเร็จ กรุณาลองใหม่จากหน้าโปรไฟล์", "Your account and questionnaire were saved, but height or weight could not be saved. Please retry from your profile.")); setSubmissionState("error"); return; }
      router.push("/");
    } catch {
      setMessage(accountCreated ? "บัญชีถูกสร้างแล้ว แต่เชื่อมต่อเพื่อบันทึกข้อมูลสุขภาพไม่ได้ กรุณาลองอีกครั้ง" : "เชื่อมต่อบริการไม่ได้ กรุณาลองใหม่อีกครั้ง"); setSubmissionState("error");
    } finally { setIsSubmitting(false); }
  }

  return (
    <div className="auth-page">
      <LanguageToggle className="auth-language-toggle" />
      <ThemeToggle className="auth-theme-toggle" />
      <main className="auth-shell">
        <section className="auth-intro" aria-label={t("เกี่ยวกับ Aphrodize", "About Aphrodize")}>
          <AuthIntroVideo />
          <Link className="auth-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-logo.svg" alt="" unoptimized />Aphrodize</Link>
          <div className="intro-copy">
            <p className="eyebrow">WELLNESS SKIN TRACKING</p>
            <h1>{t("เริ่มดูแลผิว", "Start your skin journey")}<br /><span>{t("ในแบบของคุณ", "your way")}</span></h1>
            <p>{t("สร้างบัญชีและตอบคำถามสุขภาพอย่างเป็นขั้นตอน เพื่อเริ่มติดตามผิวได้ทันที", "Create an account and answer a few guided wellness questions to personalize your tracking.")}</p>
          </div>
          <div className="intro-points"><span>✓ {t("ไม่ใช่การวินิจฉัยโรค", "Not a medical diagnosis")}</span><span>✓ {t("คุณควบคุมข้อมูลและความยินยอมได้", "You control your data and consent")}</span></div>
        </section>
        <section className="auth-card signup-card" aria-labelledby="signup-title">
          <div className="auth-card-heading">
            <p className="eyebrow">CREATE ACCOUNT · FIRST-TIME SETUP</p>
            <h2 id="signup-title">{step === "account" ? t("สร้างบัญชี", "Create your account") : t("ข้อมูลสุขภาพเบื้องต้น", "Your wellness profile")}</h2>
            <p>{step === "account" ? t("ยืนยันข้อมูลบัญชีของคุณก่อนเริ่มตอบคำถาม", "Set up your account before answering a few questions.") : t("ตอบคำถามทีละข้อ ข้อมูลนี้ใช้สำหรับการติดตามส่วนบุคคล", "Answer each question to personalize your tracking.")}</p>
          </div>
          {step === "account" ? (
            <form noValidate onSubmit={confirmAccount} aria-describedby="signup-message">
              <fieldset className="signup-section">
                <legend>{t("ข้อมูลบัญชี", "Account details")}</legend>
                <label htmlFor="name">{t("ชื่อที่แสดง", "Display name")}</label><input id="name" name="name" type="text" autoComplete="name" placeholder={t("ชื่อของคุณ", "Your name")} minLength={1} maxLength={120} required />
                <label htmlFor="email">{t("อีเมล", "Email")}</label><input id="email" name="email" type="email" autoComplete="email" placeholder="name@example.com" maxLength={320} required />
                <label htmlFor="password">{t("รหัสผ่าน", "Password")}</label><input id="password" name="password" type="password" autoComplete="new-password" placeholder={t("อย่างน้อย 8 ตัวอักษร", "At least 8 characters")} minLength={8} maxLength={128} required />
                <label htmlFor="confirm-password">{t("ยืนยันรหัสผ่าน", "Confirm password")}</label><input id="confirm-password" name="confirmPassword" type="password" autoComplete="new-password" placeholder={t("กรอกรหัสผ่านอีกครั้ง", "Enter your password again")} minLength={8} maxLength={128} required />
                <label className="checkbox signup-consent"><input type="checkbox" name="consent" required /> <span>{t("ฉันยอมรับการจัดเก็บข้อมูลตามความยินยอมก่อนวิเคราะห์ภาพ", "I agree to the consent terms for storing data before image analysis.")}</span></label>
              </fieldset>
              <p id="signup-message" className={`form-message ${submissionState}`} role="status" aria-live="polite">{message}</p>
              <button className="primary-button auth-submit" type="submit">{t("ยืนยันและไปต่อ →", "Continue →")}</button>
            </form>
          ) : (
            <form noValidate onSubmit={submitQuestions} aria-describedby="signup-message">
              <fieldset className="signup-section signup-wizard">
                <legend>{t("คำถามสุขภาพ", "Wellness questions")}</legend>
                <div className="wizard-progress" aria-label={t(`คำถาม ${questionIndex + 1} จาก ${visibleQuestions.length}`, `Question ${questionIndex + 1} of ${visibleQuestions.length}`)}>
                  <span>{t(`คำถาม ${questionIndex + 1} / ${visibleQuestions.length}`, `Question ${questionIndex + 1} / ${visibleQuestions.length}`)}</span>
                  <div aria-hidden="true"><i style={{ width: `${((questionIndex + 1) / visibleQuestions.length) * 100}%` }} /></div>
                </div>
                <div className="wizard-question">
                  <label htmlFor={questionName}>{questionIndex + 1}. {displayedQuestion}</label>
                  {(questionName === "height_cm" || questionName === "weight_kg") && <p className="metadata">{t("กรอกครั้งเดียวตอนสมัคร ค่านี้จะบันทึกในข้อมูลสมัครสมาชิกและนำมาใช้ต่อ ไม่ต้องกรอกซ้ำทุกวัน", "Enter once at signup. This value is saved with your signup information and reused; no daily re-entry is needed.")}</p>}
                  {questionName === "allergy_details" ? (
                    <><AllergyIngredients values={allergyIngredients} onChange={setAllergyIngredients} disabled={isSubmitting} /><textarea id={questionName} maxLength={500} value={answers[questionName] ?? ""} onChange={(event) => { setAnswers((current) => ({ ...current, [questionName]: event.target.value })); clearMessage(); }} disabled={isSubmitting} required={allergyIngredients.length === 0} /></>
                  ) : questionName === "age_years" || questionName === "height_cm" || questionName === "weight_kg" ? (
                    <input id={questionName} type="number" min={questionName === "age_years" ? 1 : questionName === "height_cm" ? 30 : 1} max={questionName === "age_years" ? 120 : questionName === "height_cm" ? 300 : 500} step={questionName === "age_years" ? 1 : 0.1} value={answers[questionName] ?? ""} onChange={(event) => { setAnswers((current) => ({ ...current, [questionName]: event.target.value })); clearMessage(); }} disabled={isSubmitting} required />
                  ) : (
                    <Select
                      id={questionName}
                      value={answers[questionName] ?? ""}
                      onChange={(val) => {
                        setAnswers((current) => ({ ...current, [questionName]: val }));
                        clearMessage();
                      }}
                      disabled={isSubmitting}
                      required
                      placeholder={t("เลือกคำตอบ", "Choose an answer")}
                      options={options[questionName].map(([value, thaiText]) => ({
                        value,
                        label: language === "en" ? englishOptions[questionName]?.[value] ?? thaiText : thaiText,
                      }))}
                    />
                  )}
                  {questionName === "age_years" && Number(answers.age_years) < 13 && <label className="onboarding-guardian"><input type="checkbox" checked={guardianConsent} onChange={(item) => setGuardianConsent(item.target.checked)} disabled={isSubmitting} /> <span>{t("ฉันเป็นผู้ปกครองตามกฎหมายและยินยอมให้เก็บข้อมูลนี้เพื่อการติดตามสุขภาพ", "I am the legal guardian and consent to storing these answers for wellness tracking.")}</span></label>}
                </div>
                <div className="wizard-actions">
                  <button type="button" className="secondary-button" onClick={() => setQuestionIndex((current) => current - 1)} disabled={questionIndex === 0 || isSubmitting}>{t("← ก่อนหน้า", "← Back")}</button>
                  {isLastQuestion ? <button className="primary-button" type="submit" disabled={isSubmitting}>{isSubmitting ? t("กำลังบันทึกข้อมูล…", "Saving…") : accountCreated ? t("บันทึกข้อมูลสุขภาพอีกครั้ง", "Save wellness profile again") : t("สร้างบัญชีและเริ่มใช้งาน →", "Create account and start →")}</button> : <button type="button" className="primary-button" onClick={goNext} disabled={isSubmitting}>{t("ถัดไป →", "Next →")}</button>}
                </div>
              </fieldset>
              <p id="signup-message" className={`form-message ${submissionState}`} role="status" aria-live="polite">{message}</p>
            </form>
          )}
          <p className="signup-link">{t("มีบัญชีอยู่แล้ว?", "Already have an account?")} <Link href="/login">{t("เข้าสู่ระบบ", "Sign in")}</Link></p>
          <Link className="auth-back" href="/">{t("← กลับหน้าภาพรวม", "← Back to overview")}</Link>
        </section>
      </main>
    </div>
  );
}
