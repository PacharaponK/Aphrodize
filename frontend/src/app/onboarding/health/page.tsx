"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle, useLanguage } from "@/components/language-provider";
import { useRouter, useSearchParams } from "next/navigation";
import { AllergyIngredients } from "@/components/allergy-ingredients";
import { Select } from "@/components/ui/select";

const questions = [
  ["sex", "1. เพศ", "select"],
  ["age_years", "2. อายุของคุณ (ปี)", "number"],
  ["height_cm", "3. ส่วนสูงของคุณ (เซนติเมตร)", "number"],
  ["weight_kg", "4. น้ำหนักของคุณ (กิโลกรัม)", "number"],
  ["sunscreen_frequency", "5. คุณทาครีมกันแดดบ่อยแค่ไหน?", "select"],
  ["skin_type", "6. คุณคิดว่าผิวหน้าของคุณเป็นประเภทใด?", "select"],
  ["skin_sensitivity", "7. ผิวของคุณไวต่อการระคายเคืองเพียงใด?", "select"],
  ["known_product_allergy", "8. คุณมีประวัติแพ้ผลิตภัณฑ์ดูแลผิวหรือไม่?", "select"],
  ["allergy_details", "9. โปรดระบุส่วนผสมหรือผลิตภัณฑ์ที่เคยแพ้", "text"],
  ["severe_irritation", "10. ขณะนี้มีการระคายเคืองผิวอย่างรุนแรงหรือไม่?", "select"],
  ["menstrual_tracking", "11. คุณต้องการติดตามข้อมูลรอบเดือนหรือไม่?", "select"],
  ["wellness_goal", "12. เป้าหมายหลักที่อยากติดตามคืออะไร?", "select"],
] as const;

const options: Record<string, readonly [string, string][]> = {
  sex: [["male", "ชาย"], ["female", "หญิง"], ["prefer_not_to_say", "ไม่สะดวกระบุ"]],
  sunscreen_frequency: [["never", "ไม่เคย"], ["sometimes", "บางครั้ง"], ["most_days", "เกือบทุกวัน"], ["every_day", "ทุกวัน"]],
  skin_type: [["dry", "แห้ง"], ["normal", "ปกติ"], ["combination", "ผสม"], ["oily", "มัน"], ["unsure", "ไม่แน่ใจ"]],
  skin_sensitivity: [["low", "ต่ำ"], ["medium", "ปานกลาง"], ["high", "สูง"], ["unsure", "ไม่แน่ใจ"]],
  known_product_allergy: [["no", "ไม่มีประวัติที่ทราบ"], ["yes", "มี"], ["unsure", "ไม่แน่ใจ"]],
  severe_irritation: [["no", "ไม่มี"], ["yes", "มี"], ["unsure", "ไม่แน่ใจ"]],
  menstrual_tracking: [["yes", "ต้องการ"], ["no", "ไม่ต้องการ"], ["prefer_not_to_say", "ไม่สะดวกตอบ"], ["not_applicable", "ไม่เกี่ยวข้องกับฉัน"]],
  wellness_goal: [["skin_tracking", "ติดตามผิว"], ["sleep", "การนอน"], ["hydration", "การดื่มน้ำ"], ["outdoor_habits", "กิจกรรมกลางแจ้ง"], ["general_wellness", "สุขภาพโดยรวม"]],
};

const englishQuestionLabels: Record<string, string> = {
  sex: "1. Gender", age_years: "2. Your age in years", height_cm: "3. Your height in centimetres", weight_kg: "4. Your weight in kilograms", sunscreen_frequency: "5. How often do you use sunscreen?",
  skin_type: "6. How would you describe your skin type?", skin_sensitivity: "7. How sensitive is your skin to irritation?",
  known_product_allergy: "8. Do you have any known skincare product allergies?", allergy_details: "9. Which ingredient or product caused the reaction?", severe_irritation: "10. Are you experiencing severe skin irritation now?",
  menstrual_tracking: "11. Would you like to track menstrual information?",
  wellness_goal: "12. What would you most like to track?",
};

const englishOptions: Record<string, Record<string, string>> = {
  sex: { male: "Man", female: "Woman", prefer_not_to_say: "Prefer not to say" },
  sunscreen_frequency: { never: "Never", sometimes: "Sometimes", most_days: "Most days", every_day: "Every day" },
  skin_type: { dry: "Dry", normal: "Normal", combination: "Combination", oily: "Oily", unsure: "Not sure" },
  skin_sensitivity: { low: "Low", medium: "Moderate", high: "High", unsure: "Not sure" },
  known_product_allergy: { no: "None known", yes: "Yes", unsure: "Not sure" },
  severe_irritation: { no: "No", yes: "Yes", unsure: "Not sure" },
  menstrual_tracking: { yes: "Yes, track it", no: "No", prefer_not_to_say: "Prefer not to say", not_applicable: "Not applicable to me" },
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
  const [allergyIngredients, setAllergyIngredients] = useState<string[]>([]);
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
        setAllergyIngredients(Array.isArray(saved.answers.allergy_ingredients)
          ? saved.answers.allergy_ingredients.filter((value): value is string => typeof value === "string") : []);
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
          allergy_ingredients: data.get("known_product_allergy") === "yes" ? data.getAll("allergy_ingredients") : [],
          severe_irritation: data.get("severe_irritation"),
          base_revision_id: revisionId,
        } : {
          sex: data.get("sex"),
          age_group: ageGroupForAge(submittedAge),
          age_years: submittedAge,
          height_cm: Number(data.get("height_cm")),
          weight_kg: Number(data.get("weight_kg")),
          guardian_consent: data.get("guardian_consent") === "yes",
          sunscreen_frequency: data.get("sunscreen_frequency"),
          skin_type: data.get("skin_type"),
          skin_sensitivity: data.get("skin_sensitivity"),
          known_product_allergy: data.get("known_product_allergy"),
          allergy_details: data.get("known_product_allergy") === "yes" ? data.get("allergy_details") : null,
          allergy_ingredients: data.get("known_product_allergy") === "yes" ? data.getAll("allergy_ingredients") : [],
          severe_irritation: data.get("severe_irritation"),
          menstrual_tracking: sex === "male" ? "not_applicable" : data.get("menstrual_tracking"),
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
      router.push(effectiveFullEdit ? "/profile" : "/");
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
              : sex !== "male" || name !== "menstrual_tracking";
            return included && (name !== "allergy_details" || knownProductAllergy === "yes");
          }).map(([name, label, type]) => (
            <label key={name} htmlFor={name}>
              <span>{language === "en" ? englishQuestionLabels[name] ?? label : label}</span>
              {type === "select" && (
                <Select
                  id={name}
                  name={name}
                  required
                  disabled={submitting || loadingQuestionnaire}
                  defaultValue={stringAnswer(answers, name)}
                  placeholder={t("เลือกคำตอบ", "Choose an answer")}
                  onChange={(val) => {
                    if (name === "sex") setSex(val);
                    if (name === "known_product_allergy") setKnownProductAllergy(val);
                  }}
                  options={options[name].map(([value, text]) => ({
                    value,
                    label: language === "en" ? englishOptions[name]?.[value] ?? text : text,
                  }))}
                />
              )}
              {type === "number" && <input id={name} name={name} type="number" required disabled={submitting || loadingQuestionnaire} defaultValue={stringAnswer(answers, name)} min={name === "age_years" ? 1 : name === "height_cm" ? 30 : 1} max={name === "age_years" ? 120 : name === "height_cm" ? 300 : 500} step={name === "age_years" ? 1 : 0.1} inputMode="decimal" onChange={name === "age_years" ? (event) => setAgeYears(event.target.value) : undefined} />}
              {type === "text" && <textarea id={name} name={name} required={allergyIngredients.length === 0} maxLength={500} disabled={submitting || loadingQuestionnaire} defaultValue={stringAnswer(answers, name)} />}
            </label>
          ))}
          {knownProductAllergy === "yes" && <AllergyIngredients values={allergyIngredients} onChange={setAllergyIngredients} disabled={submitting || loadingQuestionnaire} />}
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
