"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useRouter, useSearchParams } from "next/navigation";

const questions = [
  ["sex", "1. เพศ", "select"],
  ["age_group", "2. ช่วงอายุของคุณ", "select"],
  ["sleep_hours", "3. โดยเฉลี่ยเมื่อคืนคุณนอนกี่ชั่วโมง?", "select"],
  ["sleep_quality", "4. คุณภาพการนอนของคุณเป็นอย่างไร?", "select"],
  ["water_liters", "5. เมื่อวานคุณดื่มน้ำเปล่าประมาณกี่ลิตร?", "select"],
  ["outdoor_minutes", "6. เมื่อวานคุณทำกิจกรรมกลางแจ้งกี่นาที?", "select"],
  ["sunscreen_frequency", "7. คุณทาครีมกันแดดบ่อยแค่ไหน?", "select"],
  ["skin_type", "8. คุณคิดว่าผิวหน้าของคุณเป็นประเภทใด?", "select"],
  ["skin_sensitivity", "9. ผิวของคุณไวต่อการระคายเคืองเพียงใด?", "select"],
  ["known_product_allergy", "10. คุณมีประวัติแพ้ผลิตภัณฑ์ดูแลผิวหรือไม่?", "select"],
  ["severe_irritation", "11. ขณะนี้มีการระคายเคืองผิวอย่างรุนแรงหรือไม่?", "select"],
  ["stress_level", "12. ระดับความเครียดในช่วงสัปดาห์นี้ (1 ต่ำ – 5 สูง)", "select"],
  ["menstrual_tracking", "13. คุณต้องการติดตามข้อมูลรอบเดือนหรือไม่?", "select"],
  ["menstrual_status", "14. วันนี้คุณอยู่ระหว่างมีประจำเดือนหรือไม่?", "select"],
  ["wellness_goal", "15. เป้าหมายหลักที่อยากติดตามคืออะไร?", "select"],
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

type QuestionnaireResponse = { id: string; answers: Record<string, unknown> };

function stringAnswer(answers: Record<string, unknown>, key: string): string {
  const value = answers[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function HealthOnboardingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const safetyOnly = searchParams.get("edit") === "1";
  const fullEdit = searchParams.get("edit") === "full";
  const needsQuestionnaire = safetyOnly || fullEdit;
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sex, setSex] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
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
        setAgeGroup(stringAnswer(saved.answers, "age_group"));
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
      setMessage("กรุณาตอบคำถามและยืนยันความยินยอมให้ครบทุกข้อที่แสดง");
      form.reportValidity();
      return;
    }
    const data = new FormData(form);
    setSubmitting(true);
    setMessage("");
    try {
      if (editing && !revisionId) {
        setMessage("กำลังโหลดข้อมูลล่าสุด กรุณารอสักครู่");
        return;
      }
      const response = await fetch(effectiveSafetyOnly ? "/api/onboarding/health?safety=1" : "/api/onboarding/health", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(effectiveSafetyOnly ? {
          skin_sensitivity: data.get("skin_sensitivity"),
          known_product_allergy: data.get("known_product_allergy"),
          severe_irritation: data.get("severe_irritation"),
          base_revision_id: revisionId,
        } : {
          sex: data.get("sex"),
          age_group: data.get("age_group"),
          guardian_consent: data.get("guardian_consent") === "yes",
          sleep_hours: Number(data.get("sleep_hours")),
          sleep_quality: data.get("sleep_quality"),
          water_liters: Number(data.get("water_liters")),
          outdoor_minutes: Number(data.get("outdoor_minutes")),
          sunscreen_frequency: data.get("sunscreen_frequency"),
          skin_type: data.get("skin_type"),
          skin_sensitivity: data.get("skin_sensitivity"),
          known_product_allergy: data.get("known_product_allergy"),
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
      router.push(editing ? "/recommendation" : "/");
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
        <p className="eyebrow">FIRST-TIME SETUP · PERSONAL WELLNESS</p>
        <h1 id="health-title">{effectiveSafetyOnly ? "อัปเดตข้อมูลความปลอดภัย" : effectiveFullEdit ? "แก้ไขข้อมูลสุขภาพของคุณ" : "เริ่มจากข้อมูลสุขภาพของคุณ"}</h1>
        <p>ข้อมูลนี้เป็นสิ่งที่คุณรายงานเอง ใช้เพื่อแสดงการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์</p>
        {profileMissing && <p className="form-message" role="status">ยังไม่มีแบบสอบถามเดิม จึงเปิดแบบสอบถามฉบับเต็มให้กรอกก่อน</p>}
        <form key={revisionId || "new"} onSubmit={submit} noValidate>
          {questions.filter(([name]) => effectiveSafetyOnly ? ["skin_sensitivity", "known_product_allergy", "severe_irritation"].includes(name) : sex !== "male" || (name !== "menstrual_tracking" && name !== "menstrual_status")).map(([name, label, type]) => (
            <label key={name} htmlFor={name}>
              <span>{label}</span>
              {type === "select" && <select id={name} name={name} required disabled={submitting || loadingQuestionnaire} defaultValue={stringAnswer(answers, name)} onChange={name === "sex" ? (event) => setSex(event.target.value) : name === "age_group" ? (event) => setAgeGroup(event.target.value) : undefined}><option value="" disabled>เลือกคำตอบ</option>{options[name].map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select>}
            </label>
          ))}
          {ageGroup === "under_13" && <label className="onboarding-guardian"><input type="checkbox" name="guardian_consent" value="yes" required disabled={submitting || loadingQuestionnaire} defaultChecked={answers.guardian_consent === true} /> <span>ฉันเป็นผู้ปกครองตามกฎหมายและยินยอมให้เก็บข้อมูลที่ตอบในแบบสอบถามนี้เพื่อการติดตามสุขภาพ</span></label>}
          <p className="form-message" role="status" aria-live="polite">{message}</p>
          <button className="primary-button" type="submit" disabled={submitting || loadingQuestionnaire}>{submitting ? "กำลังบันทึก…" : editing ? "บันทึกการอัปเดต →" : "บันทึกและเริ่มใช้งาน →"}</button>
        </form>
        <Link href="/" className="auth-back">ข้ามไปก่อน</Link>
      </section>
    </main>
  );
}

export default function HealthOnboardingPage() {
  return <Suspense fallback={<main className="onboarding-page"><ThemeToggle className="onboarding-theme-toggle" /><p role="status">กำลังโหลดแบบสอบถาม…</p></main>}><HealthOnboardingForm /></Suspense>;
}
