"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage, type Language } from "@/components/language-provider";

type Recommendation = {
  category: string;
  rule_id: string;
  rule_version: string;
  rationale: string;
  input_source: "self_reported" | "daily_health_reported" | "self_reported_and_daily_health_reported" | "image_and_self_reported" | "image_and_daily_health_reported";
  input_fields: string[];
  signal_sources: string[];
  knowledge_source: {
    id: string;
    version: string;
    reference: { id: string; title: string; url: string };
  };
  wrinkle_regions?: string[];
  wrinkle_region_scores?: { region: string; score: number }[];
};

type DailyRecord = {
  source_table: "daily_health_entries" | "daily_health_outcomes";
  record_id: string;
  observed_date: string;
};

type LifestyleRecord = DailyRecord & {
  sleep_duration_minutes: number;
  water_intake_ml: number;
  outdoor_exposure_choice: number;
};

type Result = {
  demo?: boolean;
  status: "ready" | "no_recommendation" | "safety_blocked" | "pending";
  recommendations: Recommendation[];
  blocked_reason: string | null;
  image_context: { status: string; reason?: string; score_version?: string; calibration_version?: string };
  questionnaire_context: { status: "available" | "missing"; revision_id: string | null };
  daily_context: {
    status: string;
    consent?: { record_id: string; version: string };
    reported_dryness?: DailyRecord & { value: number };
    lifestyle?: LifestyleRecord;
  };
  rule_version: string;
  knowledge_base: { id: string; version: string };
  disclaimer: string;
  allergy_context?: { reported: boolean; details: string | null };
  profile_context?: { age_years: number | null; age_group: string | null; sex: string | null; sex_note: string };
};

const COPY = {
  th: {
    loading: "กำลังโหลดคำแนะนำ…",
    errorFallback: "โหลดคำแนะนำไม่สำเร็จ",
    signIn: "เข้าสู่ระบบ",
    noData: "ยังไม่มีข้อมูลคำแนะนำ",
    safetyBlocked: "หยุดคำแนะนำเพื่อความปลอดภัย",
    updateFirst: "ต้องอัปเดตข้อมูลก่อน",
    startQuestionnaire: "เริ่มตอบแบบสอบถาม →",
    updateSafety: "อัปเดตข้อมูลความปลอดภัย →",
    editProfile: "แก้ไขข้อมูลผิวและการกันแดด →",
    category: "หมวดผลิตภัณฑ์",
    source: "ที่มาของคำแนะนำ",
    dataUsed: "ข้อมูลที่ใช้:",
    imageScore: "คะแนนจากภาพ",
    dailyReported: "ข้อมูลสุขภาพรายวันที่คุณรายงาน",
    selfReported: "ข้อมูลที่คุณรายงาน",
    regions: "บริเวณคะแนนที่เผยแพร่:",
    rule: "กฎ",
    knowledgeBase: "ฐานข้อมูล",
    noGuidance: "ยังไม่มีคำแนะนำ",
    startWithData: "เริ่มจากข้อมูลที่มี",
    updateProfile: "แก้ไขข้อมูลผิวและการกันแดด →",
    supportingData: "ข้อมูลประกอบ",
    dailyHealth: "ข้อมูลสุขภาพรายวันที่คุณรายงาน",
    dryness: "ความแห้งผิว",
    sleep: "การนอน",
    water: "น้ำ",
    outdoor: "กิจกรรมกลางแจ้ง",
    minutes: "นาที",
    ml: "มล.",
    notRecorded: "ไม่ระบุ",
    usesReportedData: "ใช้เฉพาะข้อมูลที่คุณรายงานเอง; ค่าคาดการณ์จากโมเดล Daily Health ไม่ถูกใช้เพื่อแนะนำผลิตภัณฑ์",
    sourceLanguage: "คำอธิบายคำแนะนำและแหล่งอ้างอิงแสดงตามภาษาต้นฉบับ",
    imageNotUsed: "คะแนนจากภาพไม่ได้ถูกใช้:",
    imageScoreUnavailable: "คะแนนภาพไม่พร้อมใช้งาน",
    dateUnknown: "วันที่ไม่ระบุ",
  },
  en: {
    loading: "Loading guidance…",
    errorFallback: "Could not load guidance",
    signIn: "Sign in",
    noData: "No guidance data is available yet.",
    safetyBlocked: "Guidance paused for safety",
    updateFirst: "Update your information first",
    startQuestionnaire: "Start questionnaire →",
    updateSafety: "Update safety information →",
    editProfile: "Edit skin and sun-care information →",
    category: "Product category",
    source: "Why this is shown",
    dataUsed: "Information used:",
    imageScore: "Image score",
    dailyReported: "Self-reported daily health data",
    selfReported: "Self-reported information",
    regions: "Released scored areas:",
    rule: "Rule",
    knowledgeBase: "Knowledge base",
    noGuidance: "No guidance available",
    startWithData: "Start with your information",
    updateProfile: "Edit skin and sun-care information →",
    supportingData: "Supporting data",
    dailyHealth: "Your self-reported daily health data",
    dryness: "Skin dryness",
    sleep: "Sleep",
    water: "Water",
    outdoor: "Outdoor exposure",
    minutes: "min",
    ml: "ml",
    notRecorded: "Not recorded",
    usesReportedData: "Only information you reported is used. Daily Health model estimates are not used for product guidance.",
    sourceLanguage: "Guidance descriptions and references are shown in their source language.",
    imageNotUsed: "Image score not used:",
    imageScoreUnavailable: "Image score is unavailable",
    dateUnknown: "Date not specified",
  },
} as const;

const REGION_LABELS: Record<string, { th: string; en: string }> = {
  image_left_periocular: { th: "รอบดวงตาด้านซ้ายของภาพ", en: "Image-left eye area" },
  image_right_periocular: { th: "รอบดวงตาด้านขวาของภาพ", en: "Image-right eye area" },
};

const OUTDOOR_LABELS: Record<number, { th: string; en: string }> = {
  1: { th: "ต่ำกว่า 1 ชั่วโมง", en: "Under 1 hour" },
  2: { th: "1–น้อยกว่า 3 ชั่วโมง", en: "1 to under 3 hours" },
  3: { th: "3–น้อยกว่า 4 ชั่วโมง", en: "3 to under 4 hours" },
  4: { th: "4 ชั่วโมงขึ้นไป", en: "4 hours or more" },
};

const REASON_LABELS: Record<string, { th: string; en: string }> = {
  reported_severe_irritation: { th: "คุณรายงานการระคายเคืองรุนแรง", en: "You reported severe irritation." },
  reported_allergy: { th: "คุณรายงานประวัติการแพ้ผลิตภัณฑ์", en: "You reported a product allergy." },
  reported_high_sensitivity: { th: "คุณรายงานว่าผิวไวต่อการระคายเคืองสูง", en: "You reported high skin sensitivity." },
  no_supported_rule_inputs: { th: "ข้อมูลที่บันทึกยังไม่ตรงกับกฎคำแนะนำที่มี", en: "Your recorded information does not match an available guidance rule." },
  safety_screening_incomplete: { th: "กรุณาบันทึกข้อมูลความไวต่อการระคายเคืองและประวัติแพ้ผลิตภัณฑ์ก่อน", en: "Complete the skin-sensitivity and product-allergy questions first." },
  analysis_not_complete: { th: "ผลวิเคราะห์ภาพยังไม่เสร็จ", en: "Image analysis is not complete." },
  image_quality_below_threshold: { th: "คุณภาพภาพไม่ผ่านเกณฑ์", en: "The image did not meet the quality threshold." },
  wrinkle_confidence_not_released: { th: "คะแนนริ้วรอยยังไม่ผ่านเกณฑ์ความเชื่อมั่นที่เผยแพร่", en: "The wrinkle score has not met its release confidence threshold." },
  wrinkle_calibration_not_released: { th: "ยังไม่มีการเผยแพร่การปรับเทียบคะแนนริ้วรอยนี้", en: "Calibration for this wrinkle score has not been released." },
  wrinkle_provenance_incomplete: { th: "ข้อมูลรุ่นของคะแนนริ้วรอยไม่ครบ", en: "The wrinkle score version information is incomplete." },
  released_score_missing: { th: "ไม่มีคะแนนริ้วรอยที่เผยแพร่สำหรับภาพนี้", en: "No released wrinkle score is available for this image." },
  no_analysis: { th: "ยังไม่มีผลวิเคราะห์ภาพ จึงใช้ข้อมูลที่คุณกรอกเป็นหลัก", en: "No image analysis is available; profile-based guidance is used instead." },
};

function formatDate(value: string | undefined, language: Language): string {
  const copy = COPY[language];
  if (!value) return copy.dateUnknown;
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.valueOf()) ? value : new Intl.DateTimeFormat(language === "th" ? "th-TH" : "en-GB", { day: "numeric", month: "short", year: "numeric" }).format(parsed);
}

export function RecommendationPanel({ compact = false, source = "analysis", language: requestedLanguage }: {
  compact?: boolean;
  source?: "profile" | "analysis";
  language?: Language;
}) {
  const { language: contextLanguage } = useLanguage();
  const language = requestedLanguage ?? contextLanguage;
  const copy = COPY[language];
  const [data, setData] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const demo = new URLSearchParams(window.location.search).get("demo") === "1";
    const query = new URLSearchParams({ scope: source });
    if (demo) query.set("demo", "1");
    fetch(`/api/analysis/recommendations?${query.toString()}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "โหลดคำแนะนำไม่สำเร็จ");
        return body as Result;
      })
      .then((result) => { if (active) setData(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "โหลดคำแนะนำไม่สำเร็จ"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [source]);

  if (loading) return <p role="status">{copy.loading}</p>;
  if (error) {
    return <div className="recommendation-card" role="status"><p>{error || copy.errorFallback}</p>{error.includes("เข้าสู่ระบบ") && <Link className="text-button" href="/login">{copy.signIn} →</Link>}</div>;
  }
  if (!data) return <p role="status">{copy.noData}</p>;

  const reason = (key: string | null | undefined, fallback: string) => key
    ? REASON_LABELS[key]?.[language] ?? fallback
    : fallback;

  return (
    <div aria-live="polite">
      {data.demo && !compact ? <p className="recommendation-note" role="status">โหมดสาธิต: ใช้ข้อมูล fixture เพื่อทดสอบหน้าจอเท่านั้น</p> : null}
      {language === "th" && <p className="analysis-localization-note">{copy.sourceLanguage}</p>}
      {data.status === "safety_blocked" ? (
        <article className="recommendation-card recommendation-blocked"><span className="status">{copy.safetyBlocked}</span><h3>{copy.updateFirst}</h3><p>{reason(data.blocked_reason, language === "th" ? "ข้อมูลที่รายงานต้องได้รับการพิจารณาก่อน" : "Your reported information needs review first.")}</p><Link className="primary-button" href={data.questionnaire_context.status === "missing" ? "/onboarding/health" : "/onboarding/health?edit=1"}>{data.questionnaire_context.status === "missing" ? copy.startQuestionnaire : copy.updateSafety}</Link></article>
      ) : data.recommendations.length ? (
        <div className="recommendation-list">
          {data.recommendations.map((item) => (
            <article className="recommendation-card" key={item.rule_id}>
              <span className="status moderate">{copy.category}</span>
              <h3>{item.category}</h3>
              <p>{item.rationale}</p>
              {!compact && <div className="rule-box">
                <h3>{copy.source}</h3>
                <p>{copy.dataUsed} {item.signal_sources.map((source) => source === "image" ? copy.imageScore : source === "daily_health_reported" ? copy.dailyReported : copy.selfReported).join(" + ")}</p>
                {item.wrinkle_regions?.length ? <p>{copy.regions} {item.wrinkle_regions.map((region) => REGION_LABELS[region]?.[language] ?? region).join(", ")}</p> : null}
                {item.wrinkle_region_scores?.map((region) => <p key={region.region}>{REGION_LABELS[region.region]?.[language] ?? region.region}: wrinkle score {region.score.toFixed(1)} / 100</p>)}
                <p className="metadata">{copy.rule} {item.rule_id} · v{item.rule_version} · {copy.knowledgeBase} {item.knowledge_source.id} v{item.knowledge_source.version}</p>
                <p><a href={item.knowledge_source.reference.url} target="_blank" rel="noreferrer">{item.knowledge_source.reference.title} ↗</a></p>
              </div>}
            </article>
          ))}
        </div>
      ) : (
        <article className="recommendation-card recommendation-blocked"><span className="status">{copy.noGuidance}</span><h3>{copy.startWithData}</h3><p>{reason(data.blocked_reason, language === "th" ? "ข้อมูลที่บันทึกยังไม่เพียงพอสำหรับกฎคำแนะนำ" : "There is not enough recorded information for an available guidance rule.")}</p><Link className="primary-button" href={data.questionnaire_context.status === "missing" ? "/onboarding/health" : "/onboarding/health?edit=full"}>{data.questionnaire_context.status === "missing" ? copy.startQuestionnaire : copy.editProfile}</Link></article>
      )}
      {data.allergy_context?.reported && data.allergy_context.details && (
        <p className="recommendation-warning">{language === "th" ? "คุณระบุว่าแพ้" : "You reported an allergy to"}: {data.allergy_context.details}. {language === "th" ? "โปรดตรวจส่วนผสมจริงบนฉลากและหลีกเลี่ยงสิ่งที่ระบุ ระบบยังไม่สามารถยืนยันส่วนผสมของสินค้าแต่ละรายการได้" : "Check product labels and avoid the listed substances. Product ingredients are not verified by this system."}</p>
      )}
      {compact && data.profile_context && (
        <p className="metadata">{data.profile_context.age_years != null ? (language === "th" ? `พิจารณาอายุ ${data.profile_context.age_years} ปี` : `Age ${data.profile_context.age_years} considered`) : (language === "th" ? "พิจารณาช่วงอายุที่รายงาน" : "Reported age group considered")}{language === "th" ? " และข้อมูลโปรไฟล์ที่กรอกไว้; เพศไม่ถูกใช้เป็นเกณฑ์เหมารวมในการเลือกหมวดสกินแคร์" : "; profile answers considered. Gender is not used to stereotype skin-care categories."}</p>
      )}
      {!compact && (data.daily_context.reported_dryness || data.daily_context.lifestyle) && (
        <section className="recommendation-context" aria-label={copy.supportingData}>
          <div className="recommendation-context-heading"><div><p className="eyebrow">{copy.supportingData}</p><h3>{copy.dailyHealth}</h3></div></div>
          <div className="recommendation-context-grid">
            {data.daily_context.reported_dryness && <div><span>{copy.dryness} · {formatDate(data.daily_context.reported_dryness.observed_date, language)}</span><strong>{data.daily_context.reported_dryness.value} <small>/ 10</small></strong></div>}
            {data.daily_context.lifestyle && <><div><span>{copy.sleep} · {formatDate(data.daily_context.lifestyle.observed_date, language)}</span><strong>{data.daily_context.lifestyle.sleep_duration_minutes} <small>{copy.minutes}</small></strong></div><div><span>{copy.water} · {formatDate(data.daily_context.lifestyle.observed_date, language)}</span><strong>{data.daily_context.lifestyle.water_intake_ml} <small>{copy.ml}</small></strong></div><div><span>{copy.outdoor} · {formatDate(data.daily_context.lifestyle.observed_date, language)}</span><strong><small>{OUTDOOR_LABELS[data.daily_context.lifestyle.outdoor_exposure_choice]?.[language] ?? copy.notRecorded}</small></strong></div></>}
          </div>
          <p>{copy.usesReportedData}</p>
        </section>
      )}
      {!compact && data.image_context.status !== "eligible" && (
        <p className="recommendation-note">{copy.imageNotUsed} {reason(data.image_context.reason, copy.imageScoreUnavailable)}</p>
      )}
      {!compact && <><p className="metadata">กฎคำแนะนำ v{data.rule_version}{data.image_context.score_version ? ` · score ${data.image_context.score_version}` : ""}{data.image_context.calibration_version ? ` · calibration ${data.image_context.calibration_version}` : ""}</p>
      <p className="recommendation-warning">{data.disclaimer}</p></>}
    </div>
  );
}
