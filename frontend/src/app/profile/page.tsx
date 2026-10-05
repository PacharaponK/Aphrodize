"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useLanguage } from "@/components/language-provider";
import type { DailyHealthProfile } from "@/lib/daily-health-types";
import "./profile.css";

type ProfileValues = {
  age_years?: number;
  sex: string;
  age_group: string;
  skin_type: string;
  wellness_goal: string;
  sunscreen_frequency: string;
  menstrual_tracking: string;
};
type Profile = { display_name: string; email: string; profile: ProfileValues | null; answers: Record<string, unknown> | null };

const labels: Record<string, readonly [string, string]> = {
  age_years: ["อายุ", "Age"], sex: ["เพศ", "Gender"], age_group: ["ช่วงอายุ", "Age group"], height_cm: ["ส่วนสูง", "Height"], weight_kg: ["น้ำหนัก", "Weight"],
  sleep_hours: ["เวลานอน", "Sleep duration"], sleep_quality: ["คุณภาพการนอน", "Sleep quality"], water_liters: ["น้ำดื่ม", "Water intake"], outdoor_minutes: ["กิจกรรมกลางแจ้ง", "Outdoor activity"], sunscreen_frequency: ["การทาครีมกันแดด", "Sunscreen use"],
  skin_type: ["สภาพผิว", "Skin type"], skin_sensitivity: ["ความไวต่อการระคายเคือง", "Skin sensitivity"], known_product_allergy: ["ประวัติแพ้ผลิตภัณฑ์", "Product allergy"], allergy_details: ["ส่วนผสม/ผลิตภัณฑ์ที่แพ้", "Allergy details"], severe_irritation: ["การระคายเคืองรุนแรง", "Severe irritation"], stress_level: ["ระดับความเครียด", "Stress level"], menstrual_tracking: ["การติดตามรอบเดือน", "Menstrual tracking"], menstrual_status: ["สถานะรอบเดือน", "Menstrual status"], wellness_goal: ["เป้าหมายการติดตาม", "Tracking goal"],
};

const answerLabels: Record<string, Record<string, readonly [string, string]>> = {
  sex: { male: ["ชาย", "Man"], female: ["หญิง", "Woman"], prefer_not_to_say: ["ไม่สะดวกระบุ", "Prefer not to say"] },
  sleep_quality: { poor: ["ไม่ดี", "Poor"], fair: ["พอใช้", "Fair"], good: ["ดี", "Good"], excellent: ["ดีมาก", "Very good"] },
  sunscreen_frequency: { never: ["ไม่เคย", "Never"], sometimes: ["บางครั้ง", "Sometimes"], most_days: ["เกือบทุกวัน", "Most days"], every_day: ["ทุกวัน", "Every day"] },
  skin_type: { dry: ["แห้ง", "Dry"], normal: ["ปกติ", "Normal"], combination: ["ผสม", "Combination"], oily: ["มัน", "Oily"], unsure: ["ไม่แน่ใจ", "Not sure"] },
  skin_sensitivity: { low: ["ต่ำ", "Low"], medium: ["ปานกลาง", "Moderate"], high: ["สูง", "High"], unsure: ["ไม่แน่ใจ", "Not sure"] },
  known_product_allergy: { no: ["ไม่มีประวัติที่ทราบ", "None known"], yes: ["มี", "Yes"], unsure: ["ไม่แน่ใจ", "Not sure"] },
  severe_irritation: { no: ["ไม่มี", "No"], yes: ["มี", "Yes"], unsure: ["ไม่แน่ใจ", "Not sure"] },
  menstrual_tracking: { yes: ["ต้องการ", "Yes, track it"], no: ["ไม่ต้องการ", "No"], prefer_not_to_say: ["ไม่สะดวกตอบ", "Prefer not to say"], not_applicable: ["ไม่เกี่ยวข้องกับฉัน", "Not applicable to me"] },
  menstrual_status: { on_period: ["อยู่ระหว่างมีประจำเดือน", "I am currently menstruating"], not_on_period: ["ไม่ได้อยู่ระหว่างมีประจำเดือน", "I am not currently menstruating"], unsure: ["ไม่แน่ใจ", "Not sure"], prefer_not_to_say: ["ไม่สะดวกตอบ", "Prefer not to say"], not_applicable: ["ไม่เกี่ยวข้อง", "Not applicable"] },
  wellness_goal: { skin_tracking: ["ติดตามผิว", "Skin tracking"], sleep: ["การนอน", "Sleep"], hydration: ["การดื่มน้ำ", "Hydration"], outdoor_habits: ["กิจกรรมกลางแจ้ง", "Outdoor activity"], general_wellness: ["สุขภาพโดยรวม", "General wellness"] },
};

function displayValue(value: unknown, key: string, language: "th" | "en"): string {
  if (value == null || value === "") return language === "en" ? "Not recorded" : "ยังไม่ได้บันทึก";
  const raw = String(value ?? "-");
  const labelled = answerLabels[key]?.[raw];
  if (labelled) return labelled[language === "en" ? 1 : 0];
  if (key === "age_years") return language === "en" ? `${raw} years` : `${raw} ปี`;
  if (key === "height_cm") return `${raw} cm`;
  if (key === "weight_kg") return `${raw} kg`;
  if (key === "sleep_hours") return language === "en" ? `${raw} hours` : `${raw} ชั่วโมง`;
  if (key === "water_liters") return language === "en" ? `${raw} litres` : `${raw} ลิตร`;
  if (key === "outdoor_minutes") return language === "en" ? `${raw} minutes` : `${raw} นาที`;
  if (value === "not_applicable") return language === "en" ? "Not applicable" : "ไม่เกี่ยวข้อง";
  if (value === "prefer_not_to_say") return language === "en" ? "Prefer not to say" : "ไม่สะดวกระบุ";
  return raw.replaceAll("_", " ");
}

type MenstrualCheckin = { id: string; local_date: string; currently_menstruating: boolean; created_at: string };

function todayInBangkok(): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Bangkok", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function shiftCalendarDate(value: string, days: number): string {
  const [year, month, day] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + days));
  return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}-${String(shifted.getUTCDate()).padStart(2, "0")}`;
}

function MenstrualCycleCalendar() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [items, setItems] = useState<MenstrualCheckin[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingDate, setSavingDate] = useState<string | null>(null);
  const [consentRequired, setConsentRequired] = useState(false);
  const [consenting, setConsenting] = useState(false);
  const today = todayInBangkok();
  const [month, setMonth] = useState(() => `${today.slice(0, 7)}-01`);

  useEffect(() => {
    let active = true;
    fetch("/api/daily-health/menstrual-checkins?limit=90", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "โหลดข้อมูลรอบเดือนไม่สำเร็จ");
        if (!Array.isArray(body?.items)) throw new Error("โหลดข้อมูลรอบเดือนไม่สำเร็จ");
        return { items: body.items as MenstrualCheckin[], consentRequired: body.consent_required === true };
      })
      .then(({ items: records, consentRequired: required }) => { if (active) { setItems(records); setConsentRequired(required); } })
      .catch((error: unknown) => { if (active) setMessage(error instanceof Error ? error.message : "โหลดข้อมูลรอบเดือนไม่สำเร็จ"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const recordsByDate = new Map(items.map((item) => [item.local_date, item]));
  const [year, monthNumber] = month.split("-").map(Number);
  const firstWeekday = new Date(year, monthNumber - 1, 1).getDay();
  const daysInMonth = new Date(year, monthNumber, 0).getDate();
  const calendarDates = Array.from({ length: Math.ceil((firstWeekday + daysInMonth) / 7) * 7 }, (_, index) => {
    const day = index - firstWeekday + 1;
    return day < 1 || day > daysInMonth ? null : `${year}-${String(monthNumber).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  });
  const recordedPeriodDays = items.filter((item) => item.currently_menstruating).map((item) => item.local_date).sort();
  const periodStarts = recordedPeriodDays.filter((date, index) => index === 0 || shiftCalendarDate(recordedPeriodDays[index - 1], 1) !== date);
  const intervals = periodStarts.slice(1).map((date, index) => {
    const [startYear, startMonth, startDay] = periodStarts[index].split("-").map(Number);
    const [endYear, endMonth, endDay] = date.split("-").map(Number);
    return Math.round((Date.UTC(endYear, endMonth - 1, endDay) - Date.UTC(startYear, startMonth - 1, startDay)) / 86_400_000);
  }).filter((interval) => interval >= 21 && interval <= 45);
  const averageCycleDays = intervals.length ? Math.round(intervals.reduce((sum, interval) => sum + interval, 0) / intervals.length) : null;
  const nextPeriodEstimate = averageCycleDays && periodStarts.length >= 2
    ? shiftCalendarDate(periodStarts[periodStarts.length - 1], averageCycleDays)
    : null;
  const formatDate = (date: string) => new Intl.DateTimeFormat(language === "en" ? "en-GB" : "th-TH", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Bangkok" }).format(new Date(`${date}T12:00:00+07:00`));
  const monthLabel = new Intl.DateTimeFormat(language === "en" ? "en-GB" : "th-TH", { month: "long", year: "numeric", timeZone: "Asia/Bangkok" }).format(new Date(`${month}T12:00:00+07:00`));

  async function toggleDate(date: string) {
    if (date > today || savingDate || consentRequired) return;
    const currentlyMenstruating = recordsByDate.get(date)?.currently_menstruating ?? false;
    setSavingDate(date);
    setMessage("");
    try {
      const response = await fetch("/api/daily-health/menstrual-checkins", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ local_date: date, currently_menstruating: !currentlyMenstruating }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof result?.detail === "string" ? result.detail : "บันทึกข้อมูลไม่สำเร็จ");
      setItems((current) => [...current.filter((item) => item.local_date !== date), result as MenstrualCheckin].sort((a, b) => b.local_date.localeCompare(a.local_date)));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "บันทึกข้อมูลไม่สำเร็จ");
    } finally {
      setSavingDate(null);
    }
  }

  async function grantConsent() {
    setConsenting(true);
    setMessage("");
    try {
      const response = await fetch("/api/daily-health/menstrual-checkins/consent", { method: "PUT" });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof result?.detail === "string" ? result.detail : t("บันทึกความยินยอมไม่สำเร็จ", "Could not save consent"));
      const recordsResponse = await fetch("/api/daily-health/menstrual-checkins?limit=90", { cache: "no-store" });
      const recordsBody = await recordsResponse.json().catch(() => null);
      if (!recordsResponse.ok || !Array.isArray(recordsBody?.items)) throw new Error(t("ยินยอมแล้ว แต่โหลดข้อมูลรอบเดือนไม่สำเร็จ กรุณาลองโหลดหน้าใหม่", "Consent saved, but cycle data could not be loaded. Please refresh the page."));
      setItems(recordsBody.items as MenstrualCheckin[]);
      setConsentRequired(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("บันทึกความยินยอมไม่สำเร็จ", "Could not save consent"));
    } finally {
      setConsenting(false);
    }
  }

  return (
    <section className="profile-menstrual" aria-labelledby="menstrual-checkin-title">
      <h2 id="menstrual-checkin-title">{t("ปฏิทินรอบเดือน", "Cycle calendar")}</h2>
      <p>{t("แตะวันที่ผ่านมาเพื่อบันทึกหรือแก้ไขวันที่มีประจำเดือน ข้อมูลคาดการณ์อ้างอิงจากวันที่ที่คุณบันทึก", "Tap a past date to record or edit period days. Estimates use only the dates you record.")}</p>
      {loading && <p className="form-message" role="status">{t("กำลังโหลดข้อมูล…", "Loading…")}</p>}
      {message && <p className="form-message" role="status">{message}</p>}
      {consentRequired && !loading && <div className="profile-consent-prompt">
        <p>{t("ก่อนบันทึก ระบบจะจัดเก็บวันที่เช็กอินรอบเดือนเพื่อแสดงในปฏิทิน คำนวณวันที่คาดการณ์ และใช้ประกอบคำแนะนำส่วนบุคคล ข้อมูลนี้ไม่ใช้วินิจฉัยโรค คุณเลือกไม่ยินยอมได้", "Before saving, your cycle check-in dates will be stored to show this calendar, estimate future dates, and inform personalized guidance. This is not a diagnosis, and you can choose not to consent.")}</p>
        <button type="button" className="primary-button" disabled={consenting} onClick={() => void grantConsent()}>{consenting ? t("กำลังบันทึก…", "Saving…") : t("ยินยอมและเริ่มบันทึก", "Consent and start tracking")}</button>
      </div>}
      <div className="cycle-summary-grid">
        <article><span>{t("วันเริ่มรอบล่าสุดที่บันทึก", "Latest recorded period start")}</span><strong>{periodStarts.length ? formatDate(periodStarts[periodStarts.length - 1]) : "—"}</strong></article>
        <article><span>{t("รอบถัดไปโดยประมาณ", "Estimated next period")}</span><strong>{nextPeriodEstimate ? formatDate(nextPeriodEstimate) : "—"}</strong></article>
      </div>
      {!consentRequired && <div className="cycle-calendar">
        <header><button type="button" className="secondary-button" aria-label={t("เดือนก่อน", "Previous month")} onClick={() => setMonth((current) => shiftCalendarDate(`${current.slice(0, 7)}-15`, -15).slice(0, 7) + "-01")}>‹</button><h3>{monthLabel}</h3><button type="button" className="secondary-button" aria-label={t("เดือนถัดไป", "Next month")} onClick={() => setMonth((current) => shiftCalendarDate(`${current.slice(0, 7)}-15`, 35).slice(0, 7) + "-01")}>›</button></header>
        <div className="cycle-calendar-grid" role="grid" aria-label={monthLabel}>
          {["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"].map((day, index) => <span className="cycle-weekday" role="columnheader" key={day}>{language === "en" ? ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"][index] : day}</span>)}
          {calendarDates.map((date, index) => {
            if (!date) return <span className="cycle-calendar-empty" role="gridcell" key={`empty-${index}`} />;
            const active = recordsByDate.get(date)?.currently_menstruating === true;
            const estimated = nextPeriodEstimate === date;
            const disabled = date > today || savingDate !== null;
            return <div role="gridcell" key={date}><button type="button" className={`cycle-day${active ? " is-period" : ""}${estimated ? " is-estimated" : ""}${date === today ? " is-today" : ""}`} aria-pressed={active} aria-label={`${formatDate(date)}${active ? `, ${t("มีประจำเดือน", "period")}` : ""}${estimated ? `, ${t("วันเริ่มรอบโดยประมาณ", "estimated period start")}` : ""}`} disabled={disabled} onClick={() => void toggleDate(date)}>{Number(date.slice(-2))}</button></div>;
          })}
        </div>
        <div className="cycle-legend"><span><i className="is-period" />{t("วันที่บันทึกว่ามีประจำเดือน", "Recorded period day")}</span><span><i className="is-estimated" />{t("วันเริ่มรอบโดยประมาณ", "Estimated start")}</span></div>
      </div>}
      <p className="metadata">{averageCycleDays ? t(`ประมาณจาก ${periodStarts.length} วันที่เริ่มรอบที่บันทึก รอบเฉลี่ย ${averageCycleDays} วัน`, `Estimated from ${periodStarts.length} recorded period starts; average cycle ${averageCycleDays} days`) : t("บันทึกวันที่เริ่มประจำเดือนอย่างน้อย 2 รอบเพื่อแสดงวันคาดการณ์ โดยผลอาจคลาดเคลื่อนได้", "Record at least two period starts to see an estimate. Actual dates may vary.")}</p>
    </section>
  );
}

function ProfileMeasurements() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [values, setValues] = useState({ height: "", weight: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let current = true;
    fetch("/api/daily-health/profile", { cache: "no-store" })
      .then(async (response) => {
        const result = await response.json().catch(() => null);
        if (!response.ok) throw new Error("profile_load_failed");
        if (!current) return;
        const profile = result as DailyHealthProfile;
        setValues({
          height: profile.height_profile_consent_active === true && profile.height_cm != null ? String(profile.height_cm) : "",
          weight: profile.weight_profile_consent_active === true && profile.weight_kg != null ? String(profile.weight_kg) : "",
        });
        setMessage("");
      })
      .catch(() => {
        if (current) setMessage(language === "en" ? "Could not load height and weight" : "โหลดข้อมูลส่วนสูงและน้ำหนักไม่สำเร็จ");
      })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [language]);

  return (
    <section className="profile-measurements" aria-label={t("ส่วนสูงและน้ำหนักจากข้อมูลสมัครสมาชิก", "Height and weight from signup information")}>
      {message && <p className="form-message" role="status">{message}</p>}
      <div className="profile-measurement-grid">
        {[
          { kind: "height" as const, label: t("ส่วนสูง", "Height"), unit: "cm" },
          { kind: "weight" as const, label: t("น้ำหนัก", "Weight"), unit: "kg" },
        ].map(({ kind, label, unit }) => (
          <article className="profile-saved-measurement" key={kind}>
            <dl><dt>{label}</dt><dd>{loading ? t("กำลังโหลด…", "Loading…") : values[kind] ? `${values[kind]} ${unit}` : message ? t("โหลดไม่ได้", "Unavailable") : t("ยังไม่ได้บันทึก", "Not saved")}</dd></dl>
          </article>
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
  const [requiresLogin, setRequiresLogin] = useState(false);
  const menstrualSex = String(profile?.answers?.sex ?? profile?.profile?.sex ?? "").trim().toLowerCase();
  const shouldShowMenstrualCalendar = menstrualSex === "female" && profile?.answers?.menstrual_tracking === "yes";

  useEffect(() => {
    fetch("/api/profile", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (response.status === 401) {
          setRequiresLogin(true);
          return;
        }
        if (!response.ok) throw new Error(body?.detail ?? "ไม่สามารถโหลดข้อมูลโปรไฟล์ได้");
        setProfile(body);
        setRequiresLogin(false);
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setLoading(false));
  }, []);

  return <WorkspaceShell eyebrow="SKIN PROFILE" title="โปรไฟล์ผิวของคุณ" className="profile-workspace">
    <section className="workspace-panel profile-panel">
      {loading && <p className="form-message" role="status">{t("กำลังโหลดข้อมูลโปรไฟล์…", "Loading your profile…")}</p>}
      {message && <p className="form-message" role="status">{message}</p>}
      {!loading && requiresLogin && <div className="profile-auth-gate">
        <div className="profile-auth-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20a7.5 7.5 0 0 1 15 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg></div>
        <div className="profile-auth-copy"><p className="eyebrow">{t("พื้นที่สมาชิก", "MEMBER PROFILE")}</p><h2>{t("เข้าสู่ระบบเพื่อดูโปรไฟล์", "Sign in to view your profile")}</h2><p>{t("ข้อมูลสุขภาพ คำตอบที่บันทึกไว้ และคำแนะนำส่วนบุคคลของคุณจะแสดงที่นี่หลังเข้าสู่ระบบ", "Your saved wellness information, profile answers, and personalized guidance will appear here after you sign in.")}</p></div>
        <div className="profile-auth-actions"><Link className="primary-button" href="/login">{t("เข้าสู่ระบบ", "Sign in")} <span aria-hidden="true">→</span></Link><Link className="secondary-button" href="/signup">{t("สร้างบัญชีใหม่", "Create an account")}</Link></div>
      </div>}
      {profile && <>
        <div className="profile-toolbar">
          <p>{t("ข้อมูลที่คุณบันทึกไว้สำหรับการดูแลผิว", "Your saved information for skin care")}</p>
          {profile.answers || profile.profile ? <Link className="secondary-button" href="/onboarding/health?edit=full">{t("แก้ไขข้อมูลสุขภาพ", "Edit wellness information")}</Link> : null}
        </div>
        <div className="profile-layout">
          <aside className="profile-identity" aria-labelledby="profile-account-name">
            <article className="profile-account">
              <span className="profile-monogram" aria-hidden="true">{Array.from(profile.display_name.trim())[0]?.toLocaleUpperCase() || "?"}</span>
              <h2 id="profile-account-name">{profile.display_name || t("บัญชีของคุณ", "Your account")}</h2><p>{profile.email}</p>
            </article>
            <div className="profile-goal">
              <h3>{t("เป้าหมายการติดตาม", "Tracking goal")}</h3>
              <p><span className="profile-goal-tag">{displayValue((profile.answers ?? profile.profile)?.wellness_goal, "wellness_goal", language)}</span></p>
            </div>
            <p className="profile-context-note">{t("ข้อมูลผิวเป็นสิ่งที่คุณรายงาน ไม่ใช่ผลวินิจฉัย", "Skin information is self-reported, not a diagnosis.")}</p>
          </aside>
          <div className="profile-details">
            {profile.answers || profile.profile ? <ProfileInformation profile={profile} language={language} section="skin" /> :
              <div className="empty-state"><h2>{t("เริ่มสร้างโปรไฟล์ผิว", "Start your skin profile")}</h2><p>{t("ยังไม่มีข้อมูลสุขภาพเบื้องต้น", "No wellness information yet.")}</p><Link className="primary-button" href="/onboarding/health">{t("เริ่มตอบคำถาม", "Start questionnaire")}</Link></div>}
            <section className="profile-info-section" aria-labelledby="profile-signup-title">
              <h2 id="profile-signup-title">{t("ข้อมูลสมัครสมาชิก", "Signup information")}</h2>
              <ProfileMeasurements />
              <ProfileAnswerRows profile={profile} keys={SIGNUP_KEYS} language={language} />
            </section>
            {profile.answers || profile.profile ? <ProfileInformation profile={profile} language={language} section="habits" /> : null}
            {shouldShowMenstrualCalendar && <MenstrualCycleCalendar />}
          </div>
        </div>
      </>}
    </section>
  </WorkspaceShell>;
}

const SKIN_KEYS = ["skin_type", "skin_sensitivity", "sunscreen_frequency", "known_product_allergy", "allergy_details", "severe_irritation"];
const HABIT_KEYS = ["sleep_hours", "sleep_quality", "water_liters", "outdoor_minutes", "stress_level"];
const SIGNUP_KEYS = ["age_years", "age_group", "sex"];
const OMITTED_KEYS = ["height_cm", "weight_kg", "guardian_consent", "wellness_goal"];

function ProfileAnswerRows({ profile, keys, language }: { profile: Profile; keys: string[]; language: "th" | "en" }) {
  const answers = profile.answers ?? profile.profile ?? {};
  const rows = keys.filter(key => Object.hasOwn(answers, key) && !(key === "age_group" && profile.answers?.age_years != null));
  if (!rows.length) return null;
  return <dl className="profile-answers">{rows.map(key => <div key={key}>
    <dt>{labels[key]?.[language === "en" ? 1 : 0] ?? key.replaceAll("_", " ")}</dt>
    <dd>{displayValue(answers[key as keyof typeof answers], key, language)}</dd>
  </div>)}</dl>;
}

function ProfileInformation({ profile, language, section }: { profile: Profile; language: "th" | "en"; section: "skin" | "habits" }) {
  const t = (th: string, en: string) => language === "en" ? en : th;
  const answers = profile.answers ?? profile.profile ?? {};
  const otherKeys = Object.keys(answers).filter(key => ![...SKIN_KEYS, ...HABIT_KEYS, ...SIGNUP_KEYS, ...OMITTED_KEYS].includes(key));
  return <>
    {section === "skin" && <section className="profile-info-section profile-skin-section" aria-labelledby="profile-skin-title">
      <h2 id="profile-skin-title">{t("ข้อมูลผิวและข้อควรระวัง", "Skin information & precautions")}</h2>
      <p className="profile-section-note">{t("ใช้ประกอบการแนะนำผลิตภัณฑ์ตามกฎความปลอดภัย", "Used for safety-checked product recommendations.")}</p>
      {SKIN_KEYS.some(key => Object.hasOwn(answers, key)) ? <ProfileAnswerRows profile={profile} keys={SKIN_KEYS} language={language} /> : <p className="profile-section-note">{t("ยังไม่ได้บันทึกข้อมูลผิว", "Skin information is not recorded yet.")}</p>}
    </section>}
    {section === "habits" && HABIT_KEYS.some(key => Object.hasOwn(answers, key)) && <section className="profile-info-section" aria-labelledby="profile-habits-title">
      <h2 id="profile-habits-title">{t("พฤติกรรมจากแบบสอบถาม", "Questionnaire habits")}</h2>
      <p className="profile-section-note">{t("ข้อมูลตั้งต้นที่คุณตอบไว้ ไม่ใช่บันทึกของวันนี้", "Saved baseline answers, not today's readings.")}</p>
      <ProfileAnswerRows profile={profile} keys={HABIT_KEYS} language={language} />
    </section>}
    {section === "habits" && otherKeys.length > 0 && <section className="profile-info-section" aria-labelledby="profile-other-title">
      <h2 id="profile-other-title">{t("ข้อมูลเพิ่มเติม", "Additional information")}</h2>
      <ProfileAnswerRows profile={profile} keys={otherKeys} language={language} />
    </section>}
  </>;
}
