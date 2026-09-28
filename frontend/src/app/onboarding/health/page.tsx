"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const questions = [
  ["sex", "1. เพศ", "select"],
  ["age_group", "2. ช่วงอายุของคุณ", "select"],
  ["sunscreen_frequency", "3. คุณทาครีมกันแดดบ่อยแค่ไหน?", "select"],
  ["skin_type", "4. คุณคิดว่าผิวหน้าของคุณเป็นประเภทใด?", "select"],
  ["menstrual_tracking", "5. คุณต้องการติดตามข้อมูลรอบเดือนหรือไม่?", "select"],
  ["wellness_goal", "6. เป้าหมายหลักที่อยากติดตามคืออะไร?", "select"],
] as const;

const options: Record<string, readonly [string, string][]> = {
  sex: [["male", "ชาย"], ["female", "หญิง"], ["prefer_not_to_say", "ไม่สะดวกระบุ"]],
  age_group: [["under_13", "ต่ำกว่า 13 ปี"], ["13_17", "13–17 ปี"], ["18_24", "18–24 ปี"], ["25_34", "25–34 ปี"], ["35_44", "35–44 ปี"], ["45_54", "45–54 ปี"], ["55_plus", "55 ปีขึ้นไป"]],
  sunscreen_frequency: [["never", "ไม่เคย"], ["sometimes", "บางครั้ง"], ["most_days", "เกือบทุกวัน"], ["every_day", "ทุกวัน"]],
  skin_type: [["dry", "แห้ง"], ["normal", "ปกติ"], ["combination", "ผสม"], ["oily", "มัน"], ["unsure", "ไม่แน่ใจ"]],
  menstrual_tracking: [["yes", "ต้องการ"], ["no", "ไม่ต้องการ"], ["prefer_not_to_say", "ไม่สะดวกตอบ"], ["not_applicable", "ไม่เกี่ยวข้องกับฉัน"]],
  wellness_goal: [["skin_tracking", "ติดตามผิว"], ["sleep", "การนอน"], ["hydration", "การดื่มน้ำ"], ["outdoor_habits", "กิจกรรมกลางแจ้ง"], ["general_wellness", "สุขภาพโดยรวม"]],
};

export default function HealthOnboardingPage() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sex, setSex] = useState("");
  const [ageGroup, setAgeGroup] = useState("");

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
      const response = await fetch("/api/onboarding/health", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sex: data.get("sex"),
          age_group: data.get("age_group"),
          guardian_consent: data.get("guardian_consent") === "yes",
          sunscreen_frequency: data.get("sunscreen_frequency"),
          skin_type: data.get("skin_type"),
          menstrual_tracking: sex === "male" ? "not_applicable" : data.get("menstrual_tracking"),
          wellness_goal: data.get("wellness_goal"),
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setMessage(body?.detail ?? "บันทึกโปรไฟล์ไม่สำเร็จ โปรดลองอีกครั้ง");
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
    <main className="onboarding-page">
      <section className="onboarding-card" aria-labelledby="health-title">
        <p className="eyebrow">FIRST-TIME SETUP · PERSONAL WELLNESS</p>
        <h1 id="health-title">เริ่มจากข้อมูลสุขภาพของคุณ</h1>
        <p>ข้อมูลนี้เป็นสิ่งที่คุณรายงานเอง ใช้เพื่อแสดงการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์</p>
        <form onSubmit={submit} noValidate>
          {questions.filter(([name]) => sex !== "male" || name !== "menstrual_tracking").map(([name, label, type]) => (
            <label key={name} htmlFor={name}>
              <span>{label}</span>
              {type === "select" && <select id={name} name={name} required disabled={submitting} defaultValue="" onChange={name === "sex" ? (event) => setSex(event.target.value) : name === "age_group" ? (event) => setAgeGroup(event.target.value) : undefined}><option value="" disabled>เลือกคำตอบ</option>{options[name].map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select>}
            </label>
          ))}
          {ageGroup === "under_13" && <label className="onboarding-guardian"><input type="checkbox" name="guardian_consent" value="yes" required disabled={submitting} /> <span>ฉันเป็นผู้ปกครองตามกฎหมายและยินยอมให้เก็บข้อมูลที่ตอบในแบบสอบถามนี้เพื่อการติดตามสุขภาพ</span></label>}
          <p className="form-message" role="status" aria-live="polite">{message}</p>
          <button className="primary-button" type="submit" disabled={submitting}>{submitting ? "กำลังบันทึก…" : "บันทึกและเริ่มใช้งาน →"}</button>
        </form>
        <Link href="/" className="auth-back">ข้ามไปก่อน</Link>
      </section>
    </main>
  );
}
