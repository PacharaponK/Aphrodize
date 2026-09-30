"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useLanguage } from "@/components/language-provider";
import type { DailyHealthProfile } from "@/lib/daily-health-types";

type ProfileValues = {
  sex: string;
  age_group: string;
  skin_type: string;
  wellness_goal: string;
  sunscreen_frequency: string;
  menstrual_tracking: string;
};
type Profile = { display_name: string; email: string; profile: ProfileValues | null };

const labels: Record<string, readonly [string, string]> = {
  sex: ["เพศ", "Gender"], age_group: ["ช่วงอายุ", "Age group"], sunscreen_frequency: ["การทาครีมกันแดด", "Sunscreen use"],
  skin_type: ["สภาพผิว", "Skin type"], menstrual_tracking: ["การติดตามรอบเดือน", "Menstrual tracking"], wellness_goal: ["เป้าหมายการติดตาม", "Tracking goal"],
};

function displayValue(value: unknown, language: "th" | "en"): string {
  if (value === "not_applicable") return language === "en" ? "Not applicable" : "ไม่เกี่ยวข้อง";
  if (value === "prefer_not_to_say") return language === "en" ? "Prefer not to say" : "ไม่สะดวกระบุ";
  return String(value ?? "-").replaceAll("_", " ");
}

function ProfileMeasurements() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [values, setValues] = useState({ height: "", weight: "" });
  const [active, setActive] = useState({ height: false, weight: false });
  const [consented, setConsented] = useState({ height: false, weight: false });
  const [messages, setMessages] = useState({ height: "", weight: "", load: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<"height" | "weight" | null>(null);

  useEffect(() => {
    let current = true;
    fetch("/api/daily-health/profile", { cache: "no-store" })
      .then(async (response) => {
        const result = await response.json().catch(() => null);
        if (!response.ok) throw new Error("profile_load_failed");
        if (!current) return;
        const profile = result as DailyHealthProfile;
        const heightActive = profile.height_profile_consent_active === true;
        const weightActive = profile.weight_profile_consent_active === true;
        setActive({ height: heightActive, weight: weightActive });
        setConsented({ height: heightActive, weight: weightActive });
        setValues({
          height: heightActive && profile.height_cm != null ? String(profile.height_cm) : "",
          weight: weightActive && profile.weight_kg != null ? String(profile.weight_kg) : "",
        });
      })
      .catch(() => {
        if (current) setMessages((state) => ({
          ...state,
          load: language === "en" ? "Could not load height and weight" : "โหลดข้อมูลส่วนสูงและน้ำหนักไม่สำเร็จ",
        }));
      })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [language]);

  async function saveMeasurement(event: FormEvent<HTMLFormElement>, kind: "height" | "weight") {
    event.preventDefault();
    const allowStorage = consented[kind];
    if (!allowStorage && !active[kind]) return;
    setSaving(kind);
    setMessages((state) => ({ ...state, [kind]: "" }));
    const endpoint = `/api/daily-health/profile/${kind}`;
    try {
      const response = await fetch(endpoint, {
        method: allowStorage ? "POST" : "DELETE",
        headers: allowStorage ? { "Content-Type": "application/json" } : undefined,
        body: allowStorage
          ? JSON.stringify({
              consent_given: true,
              [kind === "height" ? "height_cm" : "weight_kg"]: Number(values[kind]),
            })
          : undefined,
        cache: "no-store",
      });
      if (!response.ok) throw new Error("profile_save_failed");
      setActive((state) => ({ ...state, [kind]: allowStorage }));
      if (!allowStorage) {
        setValues((state) => ({ ...state, [kind]: "" }));
        setConsented((state) => ({ ...state, [kind]: false }));
      }
      setMessages((state) => ({
        ...state,
        [kind]: allowStorage
          ? t("บันทึกข้อมูลแล้ว", "Saved to your profile")
          : t("ถอนความยินยอมและลบข้อมูลแล้ว", "Consent withdrawn and data removed"),
      }));
    } catch {
      setMessages((state) => ({
        ...state,
        [kind]: allowStorage
          ? t("บันทึกข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not save. Please try again.")
          : t("ลบข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not remove the data. Please try again."),
      }));
    } finally {
      setSaving(null);
    }
  }

  const fields = [
    { kind: "height" as const, label: t("ส่วนสูง", "Height"), unit: "cm", min: 30, max: 300, step: 0.1,
      consent: t("ยินยอมให้จัดเก็บส่วนสูงในโปรไฟล์ส่วนตัว", "I consent to storing my height in my profile."),
      note: t("ใช้แสดงในโปรไฟล์เท่านั้น ไม่ได้นำไปคำนวณคะแนนสุขภาพ", "For your profile only; it is not used to calculate health scores.") },
    { kind: "weight" as const, label: t("น้ำหนัก", "Weight"), unit: "kg", min: 1, max: 500, step: 0.1,
      consent: t("ยินยอมให้จัดเก็บน้ำหนักและใช้คำนวณเกณฑ์น้ำดื่มอ้างอิง", "I consent to storing my weight and using it for my hydration reference."),
      note: t("เมื่อถอนความยินยอม ระบบจะลบน้ำหนักและคะแนนกระหายน้ำตามสูตรที่เคยคำนวณจากค่านี้", "Withdrawing consent also removes saved weight snapshots and formula-based thirst scores derived from it.") },
  ];

  return (
    <section className="profile-measurements" aria-labelledby="profile-measurements-title">
      <h2 id="profile-measurements-title">{t("ส่วนสูงและน้ำหนัก", "Height and weight")}</h2>
      <p>{t("ข้อมูลนี้บันทึกแยกจากแบบฟอร์มรายวัน และคุณเลือกยินยอมแยกสำหรับแต่ละรายการได้", "These are profile details, separate from your daily form. Consent is managed independently for each measurement.")}</p>
      {messages.load && <p className="form-message" role="status">{messages.load}</p>}
      <div className="profile-measurement-grid">
        {fields.map(({ kind, label, unit, min, max, step, consent, note }) => (
          <form className="profile-measurement-card" key={kind} onSubmit={(event) => void saveMeasurement(event, kind)}>
            <h3>{label}</h3>
            <label htmlFor={`profile-${kind}`}>{t("ค่าปัจจุบัน", "Current value")} ({unit})</label>
            <input
              id={`profile-${kind}`}
              type="number"
              min={min}
              max={max}
              step={step}
              required={consented[kind]}
              value={values[kind]}
              onChange={(event) => setValues((state) => ({ ...state, [kind]: event.target.value }))}
              disabled={loading || saving !== null}
            />
            <label className="profile-measurement-consent">
              <input
                type="checkbox"
                checked={consented[kind]}
                onChange={(event) => setConsented((state) => ({ ...state, [kind]: event.target.checked }))}
                disabled={loading || saving !== null}
              />
              <span>{consent}</span>
            </label>
            <small>{note}</small>
            <button
              className="secondary-button"
              type="submit"
              disabled={loading || saving !== null || (consented[kind] && !values[kind]) || (!consented[kind] && !active[kind])}
            >
              {saving === kind ? t("กำลังบันทึก…", "Saving…") : consented[kind] ? t("บันทึก", "Save") : t("ถอนความยินยอมและลบ", "Withdraw consent and remove")}
            </button>
            <p className="form-message" role="status" aria-live="polite">{messages[kind]}</p>
          </form>
        ))}
      </div>
    </section>
  );
}

export default function ProfilePage() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [profile, setProfile] = useState<Profile | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/profile", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail ?? "ไม่สามารถโหลดข้อมูลโปรไฟล์ได้");
        setProfile(body);
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false));
  }, []);

  return <WorkspaceShell active="profile" eyebrow="SKIN PROFILE" title="โปรไฟล์ผิวของคุณ">
    <section className="workspace-panel profile-panel">
      {loading && <p className="form-message" role="status">{t("กำลังโหลดข้อมูลโปรไฟล์…", "Loading your profile…")}</p>}
      {message && <p className="form-message" role="status">{message}</p>}
      {profile && <><article className="profile-account"><h2>{profile.display_name}</h2><p>{profile.email}</p></article>
        <ProfileMeasurements />
        {profile.profile ? <><h2>{t("ข้อมูลสุขภาพที่บันทึกไว้", "Saved wellness information")}</h2><dl className="profile-answers">{Object.entries(profile.profile).map(([key, value]) => <div key={key}><dt>{labels[key]?.[language === "en" ? 1 : 0] ?? key}</dt><dd>{displayValue(value, language)}</dd></div>)}</dl><Link className="secondary-button" href="/onboarding/health?edit=full">{t("แก้ไขข้อมูลสุขภาพ →", "Edit wellness information →")}</Link></> : <div className="empty-state"><p>{t("ยังไม่มีข้อมูลสุขภาพเบื้องต้น", "No wellness information yet.")}</p><Link className="primary-button" href="/onboarding/health">{t("เริ่มตอบคำถาม →", "Start questionnaire →")}</Link></div>}</>}
    </section>
  </WorkspaceShell>;
}
