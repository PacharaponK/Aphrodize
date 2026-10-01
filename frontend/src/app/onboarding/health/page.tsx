"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle, useLanguage } from "@/components/language-provider";
import { useRouter, useSearchParams } from "next/navigation";

const questions = [
  ["sex", "1. เพศ", "select"],
  ["age_years", "2. อายุของคุณ (ปี)", "number"],
  ["height_cm", "3. ส่วนสูงของคุณ (เซนติเมตร)", "number"],
  ["weight_kg", "4. น้ำหนักของคุณ (กิโลกรัม)", "number"],
  ["sleep_hours", "5. โดยเฉลี่ยเมื่อคืนคุณนอนกี่ชั่วโมง?", "select"],
  ["sleep_quality", "6. คุณภาพการนอนของคุณเป็นอย่างไร?", "select"],
  ["water_liters", "7. เมื่อวานคุณดื่มน้ำเปล่าประมาณกี่ลิตร?", "select"],
  ["outdoor_minutes", "8. เมื่อวานคุณทำกิจกรรมกลางแจ้งกี่นาที?", "select"],
  ["sunscreen_frequency", "9. คุณทาครีมกันแดดบ่อยแค่ไหน?", "select"],
  ["skin_type", "10. คุณคิดว่าผิวหน้าของคุณเป็นประเภทใด?", "select"],
  ["skin_sensitivity", "11. ผิวของคุณไวต่อการระคายเคืองเพียงใด?", "select"],
  ["known_product_allergy", "12. คุณมีประวัติแพ้ผลิตภัณฑ์ดูแลผิวหรือไม่?", "select"],
  ["allergy_details", "13. โปรดระบุส่วนผสมหรือผลิตภัณฑ์ที่เคยแพ้", "text"],
  ["severe_irritation", "14. ขณะนี้มีการระคายเคืองผิวอย่างรุนแรงหรือไม่?", "select"],
  ["stress_level", "15. ระดับความเครียดในช่วงสัปดาห์นี้ (1 ต่ำ – 5 สูง)", "select"],
  ["menstrual_tracking", "16. คุณต้องการติดตามข้อมูลรอบเดือนหรือไม่?", "select"],
  ["menstrual_status", "17. วันนี้คุณอยู่ระหว่างมีประจำเดือนหรือไม่?", "select"],
  ["wellness_goal", "18. เป้าหมายหลักที่อยากติดตามคืออะไร?", "select"],
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

const englishQuestionLabels: Record<string, string> = {
  sex: "1. Gender", age_years: "2. Your age in years", height_cm: "3. Your height in centimetres", weight_kg: "4. Your weight in kilograms", sleep_hours: "5. About how many hours did you sleep last night?",
  sleep_quality: "6. How would you describe your sleep quality?", water_liters: "7. About how much plain water did you drink yesterday?",
  outdoor_minutes: "8. How many minutes did you spend outdoors yesterday?", sunscreen_frequency: "9. How often do you use sunscreen?",
  skin_type: "10. How would you describe your skin type?", skin_sensitivity: "11. How sensitive is your skin to irritation?",
  known_product_allergy: "12. Do you have any known skincare product allergies?", allergy_details: "13. Which ingredient or product caused the reaction?", severe_irritation: "14. Are you experiencing severe skin irritation now?",
  stress_level: "15. Your stress level this week (1 low – 5 high)", menstrual_tracking: "16. Would you like to track menstrual information?",
  menstrual_status: "17. Are you currently menstruating?", wellness_goal: "18. What would you most like to track?",
};

const englishOptions: Record<string, Record<string, string>> = {
  sex: { male: "Man", female: "Woman", prefer_not_to_say: "Prefer not to say" },
  sleep_hours: { "4": "Less than 5 hours", "5.5": "5–6 hours", "6.5": "6–7 hours", "7.5": "7–8 hours", "8.5": "8–9 hours", "9.5": "More than 9 hours" },
  sleep_quality: { poor: "Poor", fair: "Fair", good: "Good", excellent: "Very good" },
  water_liters: { "0.5": "Less than 1 litre", "1": "About 1 litre", "1.5": "About 1.5 litres", "2": "About 2 litres", "2.5": "About 2.5 litres", "3": "3 litres or more" },
  outdoor_minutes: { "0": "No outdoor activity", "15": "1–30 minutes", "45": "31–60 minutes", "90": "1–2 hours", "150": "More than 2 hours" },
  sunscreen_frequency: { never: "Never", sometimes: "Sometimes", most_days: "Most days", every_day: "Every day" },
  skin_type: { dry: "Dry", normal: "Normal", combination: "Combination", oily: "Oily", unsure: "Not sure" },
  skin_sensitivity: { low: "Low", medium: "Moderate", high: "High", unsure: "Not sure" },
  known_product_allergy: { no: "None known", yes: "Yes", unsure: "Not sure" },
  severe_irritation: { no: "No", yes: "Yes", unsure: "Not sure" },
  stress_level: { "1": "1 — Very low", "2": "2", "3": "3 — Moderate", "4": "4", "5": "5 — Very high" },
  menstrual_tracking: { yes: "Yes, track it", no: "No", prefer_not_to_say: "Prefer not to say", not_applicable: "Not applicable to me" },
  menstrual_status: { on_period: "I am currently menstruating", not_on_period: "I am not currently menstruating", unsure: "Not sure", prefer_not_to_say: "Prefer not to say" },
  wellness_goal: { skin_tracking: "Skin tracking", sleep: "Sleep", hydration: "Hydration", outdoor_habits: "Outdoor activity", general_wellness: "General wellness" },
};

type QuestionnaireResponse = { id: string; answers: Record<string, unknown> };

function stringAnswer(answers: Record<string, unknown>, key: string): string {
  const value = answers[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function ageGroupForAge(age: number): string {
  if (age < 13) return "under_13";
  if (age < 18) return "13_17";
  if (age < 25) return "18_24";
  if (age < 35) return "25_34";
  if (age < 45) return "35_44";
  if (age < 55) return "45_54";
  return "55_plus";
}

function HealthOnboardingForm() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const router = useRouter();
  const searchParams = useSearchParams();
  const safetyOnly = searchParams.get("edit") === "1";
  const fullEdit = searchParams.get("edit") === "full";
  const needsQuestionnaire = safetyOnly || fullEdit;
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sex, setSex] = useState("");
  const [knownProductAllergy, setKnownProductAllergy] = useState("");
  const [ageYears, setAgeYears] = useState("");
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [revisionId, setRevisionId] = useState("");
  const [loadingQuestionnaire, setLoadingQuestionnaire] = useState(needsQuestionnaire);
  const [profileMissing, setProfileMissing] = useState(false);
  const effectiveSafetyOnly = safetyOnly && !profileMissing;
  const effectiveFullEdit = fullEdit && !profileMissing;
  const editing = effectiveSafetyOnly || effectiveFullEdit;

  useEffect(() => {
    if (!needsQuestionnaire) return;
    let active = true;
    fetch("/api/onboarding/health", { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 404) return null;
        const body = await response.json().catch(() => null);
        if (!response.ok || !body || typeof body.id !== "string" || typeof body.answers !== "object") {
          throw new Error(typeof body?.detail === "string" ? body.detail : "โหลดข้อมูลแบบสอบถามไม่สำเร็จ");
        }
        return body as QuestionnaireResponse;
      })
      .then((saved) => {
        if (!active) return;
        if (saved === null) {
          setProfileMissing(true);
          return;
        }
        setAnswers(saved.answers);
        setRevisionId(saved.id);
        setSex(stringAnswer(saved.answers, "sex"));
        setKnownProductAllergy(stringAnswer(saved.answers, "known_product_allergy"));
        setAgeYears(stringAnswer(saved.answers, "age_years"));
      })
      .catch((reason: unknown) => {
        if (active) setMessage(reason instanceof Error ? reason.message : "โหลดข้อมูลแบบสอบถามไม่สำเร็จ");
      })
      .finally(() => { if (active) setLoadingQuestionnaire(false); });
    return () => { active = false; };
  }, [needsQuestionnaire]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      setMessage(t("กรุณาตอบคำถามและยืนยันความยินยอมให้ครบทุกข้อที่แสดง", "Please answer each required question and confirm consent."));
      form.reportValidity();
      return;
    }
    const data = new FormData(form);
    const submittedAge = Number(data.get("age_years"));
    setSubmitting(true);
    setMessage("");
    try {
      if (editing && !revisionId) {
        setMessage(t("กำลังโหลดข้อมูลล่าสุด กรุณารอสักครู่", "Loading your latest information. Please wait."));
        return;
      }
      const response = await fetch(effectiveSafetyOnly ? "/api/onboarding/health?safety=1" : "/api/onboarding/health", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(effectiveSafetyOnly ? {
          skin_sensitivity: data.get("skin_sensitivity"),
          known_product_allergy: data.get("known_product_allergy"),
          allergy_details: data.get("known_product_allergy") === "yes" ? data.get("allergy_details") : null,
          severe_irritation: data.get("severe_irritation"),
          base_revision_id: revisionId,
        } : {
          sex: data.get("sex"),
          age_group: ageGroupForAge(submittedAge),
          age_years: submittedAge,
          height_cm: Number(data.get("height_cm")),
          weight_kg: Number(data.get("weight_kg")),
          guardian_consent: data.get("guardian_consent") === "yes",
          sleep_hours: Number(data.get("sleep_hours")),
          sleep_quality: data.get("sleep_quality"),
          water_liters: Number(data.get("water_liters")),
          outdoor_minutes: Number(data.get("outdoor_minutes")),
          sunscreen_frequency: data.get("sunscreen_frequency"),
          skin_type: data.get("skin_type"),
          skin_sensitivity: data.get("skin_sensitivity"),
          known_product_allergy: data.get("known_product_allergy"),
          allergy_details: data.get("known_product_allergy") === "yes" ? data.get("allergy_details") : null,
          severe_irritation: data.get("severe_irritation"),
          stress_level: Number(data.get("stress_level")),
          menstrual_tracking: sex === "male" ? "not_applicable" : data.get("menstrual_tracking"),
          menstrual_status: sex === "male" ? "not_applicable" : data.get("menstrual_status"),
          wellness_goal: data.get("wellness_goal"),
          ...(effectiveFullEdit ? { base_revision_id: revisionId } : {}),
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setMessage(body?.detail ?? "บันทึกแบบสอบถามไม่สำเร็จ โปรดลองอีกครั้ง");
        return;
      }
      if (!effectiveSafetyOnly) {
        const measurementRequests = [
          ["height", "height_cm", Number(data.get("height_cm"))],
          ["weight", "weight_kg", Number(data.get("weight_kg"))],
        ] as const;
        const measurementResponses = await Promise.all(measurementRequests.map(([kind, key, value]) => fetch(`/api/daily-health/profile/${kind}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ [key]: value, consent_given: true }),
        })));
        if (measurementResponses.some((measurement) => !measurement.ok)) {
          setMessage(t("บันทึกแบบสอบถามแล้ว แต่บันทึกส่วนสูงหรือน้ำหนักไม่สำเร็จ กรุณาลองแก้ไขโปรไฟล์อีกครั้ง", "Your questionnaire was saved, but height or weight could not be saved. Please edit your profile again."));
          return;
        }
      }
      router.push(effectiveFullEdit ? "/profile" : editing ? "/recommendation" : "/");
    } catch {
      setMessage("เชื่อมต่อบริการไม่ได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="onboarding-page">
      <ThemeToggle className="onboarding-theme-toggle" />
      <section className="onboarding-card" aria-labelledby="health-title">
        <div className="onboarding-controls"><LanguageToggle /><ThemeToggle className="onboarding-theme-toggle" /></div>
        <p className="eyebrow">{t("เริ่มต้นใช้งาน · ดูแลสุขภาพส่วนบุคคล", "FIRST-TIME SETUP · PERSONAL WELLNESS")}</p>
        <h1 id="health-title">{effectiveSafetyOnly ? t("อัปเดตข้อมูลความปลอดภัย", "Update safety information") : effectiveFullEdit ? t("แก้ไขข้อมูลสุขภาพของคุณ", "Edit your wellness information") : t("เริ่มจากข้อมูลสุขภาพของคุณ", "Start with your wellness information")}</h1>
        <p>{t("ข้อมูลนี้เป็นสิ่งที่คุณรายงานเอง ใช้เพื่อแสดงการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์", "This self-reported information supports personal tracking; it is not a medical diagnosis.")}</p>
        {profileMissing && <p className="form-message" role="status">{t("ยังไม่มีแบบสอบถามเดิม จึงเปิดแบบสอบถามฉบับเต็มให้กรอกก่อน", "No saved questionnaire was found, so the full questionnaire is shown.")}</p>}
        <form key={revisionId || "new"} onSubmit={submit} noValidate>
          {questions.filter(([name]) => {
            const included = effectiveSafetyOnly
              ? ["skin_sensitivity", "known_product_allergy", "allergy_details", "severe_irritation"].includes(name)
              : sex !== "male" || (name !== "menstrual_tracking" && name !== "menstrual_status");
            return included && (name !== "allergy_details" || knownProductAllergy === "yes");
          }).map(([name, label, type]) => (
            <label key={name} htmlFor={name}>
              <span>{language === "en" ? englishQuestionLabels[name] ?? label : label}</span>
              {type === "select" && <select id={name} name={name} required disabled={submitting || loadingQuestionnaire} defaultValue={stringAnswer(answers, name)} onChange={name === "sex" ? (event) => setSex(event.target.value) : name === "known_product_allergy" ? (event) => setKnownProductAllergy(event.target.value) : undefined}><option value="" disabled>{t("เลือกคำตอบ", "Choose an answer")}</option>{options[name].map(([value, text]) => <option key={value} value={value}>{language === "en" ? englishOptions[name]?.[value] ?? text : text}</option>)}</select>}
              {type === "number" && <input id={name} name={name} type="number" required disabled={submitting || loadingQuestionnaire} defaultValue={stringAnswer(answers, name)} min={name === "age_years" ? 1 : name === "height_cm" ? 30 : 1} max={name === "age_years" ? 120 : name === "height_cm" ? 300 : 500} step={name === "age_years" ? 1 : 0.1} inputMode="decimal" onChange={name === "age_years" ? (event) => setAgeYears(event.target.value) : undefined} />}
              {type === "text" && <textarea id={name} name={name} required maxLength={500} disabled={submitting || loadingQuestionnaire} defaultValue={stringAnswer(answers, name)} />}
            </label>
          ))}
          {ageYears !== "" && Number(ageYears) < 13 && <label className="onboarding-guardian"><input type="checkbox" name="guardian_consent" value="yes" required disabled={submitting || loadingQuestionnaire} defaultChecked={answers.guardian_consent === true} /> <span>{t("ฉันเป็นผู้ปกครองตามกฎหมายและยินยอมให้เก็บข้อมูลที่ตอบในแบบสอบถามนี้เพื่อการติดตามสุขภาพ", "I am the legal guardian and consent to collecting these questionnaire responses for wellness tracking.")}</span></label>}
          <p className="form-message" role="status" aria-live="polite">{message}</p>
          <button className="primary-button" type="submit" disabled={submitting || loadingQuestionnaire}>{submitting ? t("กำลังบันทึก…", "Saving…") : editing ? t("บันทึกการอัปเดต →", "Save updates →") : t("บันทึกและเริ่มใช้งาน →", "Save and continue →")}</button>
        </form>
        <Link href="/" className="auth-back">{t("ข้ามไปก่อน", "Skip for now")}</Link>
      </section>
    </main>
  );
}

export default function HealthOnboardingPage() {
  return <Suspense fallback={<main className="onboarding-page"><p role="status">Loading questionnaire…</p></main>}><HealthOnboardingForm /></Suspense>;
}
