"use client";

import Link from "next/link";
import { ArrowRight, LockKeyhole, Store, Globe } from "lucide-react";
import { Select } from "@/components/ui/select";
import { useEffect, useState } from "react";
import { useLanguage, type Language } from "@/components/language-provider";
import { ALLERGY_INGREDIENTS } from "@/components/allergy-ingredients";

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
  products?: {
    id: string; brand: string; name: string; variant: string;
    price_satang: number | null; price_checked_at: string | null;
    market?: string | null; price_source_url?: string | null; application_regions?: string[];
    ingredients_inci: string[]; warnings_label: string;
    source_url: string; reviewed_at: string;
    matched_skin_type: string; matched_claims: string[];
  }[];
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
  allergy_context?: { reported: boolean; details: string | null; ingredients?: string[] };
  profile_context?: { skin_type: string; skin_sensitivity: string; age_years: number | null; age_group: string | null; sex: string | null; sex_note: string };
  product_context?: { status: string };
};

const COPY = {
  th: {
    loading: "กำลังโหลดคำแนะนำ…",
    errorFallback: "โหลดคำแนะนำไม่สำเร็จ",
    signIn: "เข้าสู่ระบบ",
    signInRequired: "กรุณาเข้าสู่ระบบเพื่อดูคำแนะนำส่วนบุคคล",
    signInHint: "เข้าสู่ระบบเพื่อดูคำแนะนำที่อ้างอิงจากข้อมูลผิวของคุณ",
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
    signInRequired: "Sign in to view your personalized guidance.",
    signInHint: "Sign in to see guidance based on your skin profile.",
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
  forehead: { th: "หน้าผาก", en: "Forehead" },
  glabella: { th: "ระหว่างคิ้ว", en: "Glabella" },
  image_left_periocular: { th: "รอบดวงตาด้านซ้ายของภาพ", en: "Image-left eye area" },
  image_right_periocular: { th: "รอบดวงตาด้านขวาของภาพ", en: "Image-right eye area" },
  image_left_cheek: { th: "แก้มซ้ายของภาพ", en: "Image-left cheek" },
  image_right_cheek: { th: "แก้มขวาของภาพ", en: "Image-right cheek" },
  nasolabial: { th: "ร่องแก้ม", en: "Nasolabial fold" },
  perioral: { th: "รอบปาก", en: "Perioral area" },
};

const SKIN_LABELS: Record<string, { th: string; en: string }> = {
  dry: { th: "ผิวแห้ง", en: "Dry skin" }, normal: { th: "ผิวปกติ", en: "Normal skin" },
  oily: { th: "ผิวมัน", en: "Oily skin" }, combination: { th: "ผิวผสม", en: "Combination skin" },
  unsure: { th: "ยังไม่ทราบประเภทผิว", en: "Skin type unknown" },
  all: { th: "ทุกประเภทผิวตามฉลาก", en: "All skin types on the label" },
};

const OUTDOOR_LABELS: Record<number, { th: string; en: string }> = {
  1: { th: "ต่ำกว่า 1 ชั่วโมง", en: "Under 1 hour" },
  2: { th: "1–น้อยกว่า 3 ชั่วโมง", en: "1 to under 3 hours" },
  3: { th: "3–น้อยกว่า 4 ชั่วโมง", en: "3 to under 4 hours" },
  4: { th: "4 ชั่วโมงขึ้นไป", en: "4 hours or more" },
};

const REASON_LABELS: Record<string, { th: string; en: string }> = {
  profile_consent_required: { th: "ไม่มีความยินยอมที่ยังใช้งานได้สำหรับใช้ข้อมูลโปรไฟล์", en: "Active consent is required to use your profile." },
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
  const [market, setMarket] = useState("TH");
  const [maxPrice, setMaxPrice] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const query = new URLSearchParams({ scope: source, market });
    if (maxPrice !== null) query.set("max_price_satang", String(maxPrice));
    function load() {
      fetch(`/api/analysis/recommendations?${query.toString()}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "โหลดคำแนะนำไม่สำเร็จ");
        return body as Result;
      })
      .then((result) => {
        if (!active) return;
        setData(result);
        if (result.status === "pending") timer = setTimeout(load, 2500);
      })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "โหลดคำแนะนำไม่สำเร็จ"); })
      .finally(() => { if (active) setLoading(false); });
    }
    load();
    return () => { active = false; clearTimeout(timer); };
  }, [source, market, maxPrice]);

  if (loading) return <p role="status">{copy.loading}</p>;
  if (error) {
    if (compact) {
      const loginRequired = error.includes("เข้าสู่ระบบ") || error.toLowerCase().includes("sign in");
      return <div className={`recommendation-inline-state${loginRequired ? " is-auth-required" : ""}`} role="status">
        {loginRequired && <span className="recommendation-inline-icon" aria-hidden="true"><LockKeyhole size={19} /></span>}
        <div className="recommendation-inline-copy"><p>{loginRequired ? copy.signInRequired : error || copy.errorFallback}</p>{loginRequired && <small>{copy.signInHint}</small>}</div>
        {loginRequired && <Link className="primary-button" href="/login">{copy.signIn}<ArrowRight size={16} aria-hidden="true" /></Link>}
      </div>;
    }
    return <div className="recommendation-card" role="status"><p>{error || copy.errorFallback}</p>{error.includes("เข้าสู่ระบบ") && <Link className="text-button" href="/login">{copy.signIn} →</Link>}</div>;
  }
  if (!data) return <p role="status">{copy.noData}</p>;
  if (data.status === "pending") return <p role="status">{language === "th" ? "รอวิเคราะห์ภาพสำเร็จก่อนแนะนำผลิตภัณฑ์" : "Product guidance will be available after image analysis completes."}</p>;

  const reason = (key: string | null | undefined, fallback: string) => key
    ? REASON_LABELS[key]?.[language] ?? fallback
    : fallback;

  return (
    <div aria-live="polite">
      <form className="recommendation-filters" onSubmit={(event) => {
        event.preventDefault();
        const values = new FormData(event.currentTarget);
        const price = String(values.get("budget") ?? "");
        const [baht, satang = ""] = price.split(".");
        const nextMarket = String(values.get("market") ?? "TH");
        const nextPrice = price === "" ? null : Number(baht) * 100 + Number(satang.padEnd(2, "0"));
        if (nextMarket !== market || nextPrice !== maxPrice) {
          setLoading(true);
          setError("");
          setMarket(nextMarket);
          setMaxPrice(nextPrice);
        }
      }}>
        <label>
          <span className="filter-label">{language === "th" ? "ตลาดสินค้า" : "Product market"}</span>
          <Select
            name="market"
            defaultValue={market}
            value={market}
            onChange={(val) => {
              setMarket(val);
              setLoading(true);
              setError("");
            }}
            options={[
              {
                value: "TH",
                label: language === "th" ? "จำหน่ายในไทย" : "Sold in Thailand",
                description: language === "th" ? "เฉพาะสินค้าที่มีจำหน่ายในประเทศไทย" : "Available in Thailand",
                icon: <Store size={15} />,
              },
              {
                value: "all",
                label: language === "th" ? "ทุกตลาด" : "All markets",
                description: language === "th" ? "รวมสินค้าทุกตลาดและสินค้านำเข้า" : "All international markets",
                icon: <Globe size={15} />,
              },
            ]}
          />
        </label>
        <label>
          <span className="filter-label">{language === "th" ? "งบสูงสุดต่อสินค้า (บาท)" : "Maximum per product (THB)"}</span>
          <input name="budget" type="number" min="0" max="1000000" step="0.01" inputMode="decimal" placeholder={language === "th" ? "ไม่จำกัด" : "No limit"} defaultValue={maxPrice === null ? "" : maxPrice / 100} />
        </label>
        <button className="secondary-button" type="submit">{language === "th" ? "ใช้ตัวกรอง" : "Apply filters"}</button>
        {maxPrice !== null && <small>{language === "th" ? "ใช้เฉพาะราคาที่มีแหล่งอ้างอิงและตรวจสอบใน 30 วันล่าสุด งบนี้ต่อสินค้า ไม่ใช่ราคารวมทั้งชุด" : "Uses sourced prices checked within 30 days. This limit applies to each product, not the whole routine."}</small>}
      </form>
      {language === "th" && <p className="analysis-localization-note">{copy.sourceLanguage}</p>}
      {data.profile_context && <p>{language === "th" ? "ข้อมูลผิวที่ใช้: " : "Skin profile used: "}{SKIN_LABELS[data.profile_context.skin_type]?.[language] ?? copy.notRecorded}{language === "th" ? " · ความไวต่อการระคายเคือง: " : " · Sensitivity: "}{data.profile_context.skin_sensitivity === "medium" ? (language === "th" ? "ปานกลาง" : "Moderate") : (language === "th" ? "ต่ำ" : "Low")} · <Link href="/profile">{language === "th" ? "ดูโปรไฟล์" : "View profile"}</Link></p>}
      {data.status === "safety_blocked" ? (
        <article className="recommendation-card recommendation-blocked"><span className="status">{copy.safetyBlocked}</span><h3>{copy.updateFirst}</h3><p>{reason(data.blocked_reason, language === "th" ? "ข้อมูลที่รายงานต้องได้รับการพิจารณาก่อน" : "Your reported information needs review first.")}</p>{data.blocked_reason !== "profile_consent_required" && <Link className="primary-button" href={data.questionnaire_context.status === "missing" ? "/onboarding/health" : "/onboarding/health?edit=1"}>{data.questionnaire_context.status === "missing" ? copy.startQuestionnaire : copy.updateSafety}</Link>}</article>
      ) : data.recommendations.length ? (
        <div className="recommendation-list">
          {data.recommendations.map((item) => (
            <article className="recommendation-card" key={item.rule_id}>
              <span className="status moderate">{copy.category}</span>
              <h3>{item.category}</h3>
              <p>{item.rationale}</p>
              {item.products?.length ? <div className="recommendation-list" aria-label={language === "th" ? "ผลิตภัณฑ์จากแค็ตตาล็อกที่ตรวจทานแล้ว" : "Products from the reviewed catalog"}>
                {item.products.map((product) => <div className="rule-box recommendation-product" key={product.id}>
                  <h4>{product.brand} · {product.name}{product.variant ? ` · ${product.variant}` : ""}</h4>
                  <p>{language === "th" ? "ประเภทผิวตามฉลาก: " : "Label skin type: "}{SKIN_LABELS[product.matched_skin_type]?.[language] ?? product.matched_skin_type}{product.matched_claims.length > 0 && ` · ${product.matched_claims.join(", ")}`}</p>
                  {product.price_satang != null && <p>{new Intl.NumberFormat(language === "th" ? "th-TH" : "en-GB", { style: "currency", currency: "THB" }).format(product.price_satang / 100)} · {language === "th" ? "ราคาอ้างอิง ตรวจเมื่อ " : "Reference price checked "}{formatDate(product.price_checked_at?.split("T")[0], language)}</p>}
                  {product.warnings_label && <p className="recommendation-warning">{product.warnings_label}</p>}
                  <details><summary>{language === "th" ? "ดูส่วนผสม INCI ที่ตรวจทานแล้ว" : "View reviewed INCI ingredients"}</summary><p>{product.ingredients_inci.join(", ")}</p></details>
                  <p>{product.price_source_url && <><a href={product.price_source_url} target="_blank" rel="noreferrer">{language === "th" ? "แหล่งราคาและขนาดสินค้า" : "Price and pack size source"} ↗</a> · </>}<a href={product.source_url} target="_blank" rel="noreferrer">{language === "th" ? "ข้อมูลผลิตภัณฑ์จากแหล่งอ้างอิง" : "Product source"} ↗</a></p>
                  <p className="metadata">{language === "th" ? "ตรวจข้อมูลเมื่อ " : "Catalog reviewed "}{formatDate(product.reviewed_at.split("T")[0], language)} · {language === "th" ? "การจับคู่จากฉลากไม่รับประกันว่าจะไม่แพ้ โปรดตรวจสูตรปัจจุบันก่อนใช้" : "Label matching does not guarantee against allergy. Check the current formula before use."}</p>
                </div>)}
              </div> : data.product_context?.status !== "allergy_review_required" && <p className="metadata">{language === "th" ? "ยังไม่มีผลิตภัณฑ์ที่ตรวจทานแล้วตรงกับเงื่อนไขนี้" : "No reviewed product matches this guidance yet."}</p>}
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
      {data.allergy_context?.reported && (
        <p className="recommendation-warning">{language === "th" ? "คุณรายงานประวัติแพ้" : "You reported an allergy"}{data.allergy_context.details ? `: ${data.allergy_context.details}` : ""}. {language === "th" ? "ระบบงดเลือกสินค้ารายชิ้น แม้บันทึกสารที่แพ้แล้ว การตรวจชื่อส่วนผสมและสารที่เกี่ยวข้องยังไม่ครบถ้วน โปรดให้ผู้เชี่ยวชาญตรวจฉลากจริงก่อนเลือกใช้" : "Named products are withheld because recorded allergens cannot reliably resolve every ingredient and related substance. Have a professional review the current label before use."}</p>
      )}
      {!!data.allergy_context?.ingredients?.length && <p>{language === "th" ? "สารที่รายงานว่าแพ้: " : "Reported allergens: "}{data.allergy_context.ingredients.map((value) => { const entry = ALLERGY_INGREDIENTS.find(([key]) => key === value); return entry ? entry[language === "th" ? 1 : 2] : value; }).join(", ")}</p>}
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
