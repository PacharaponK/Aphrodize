"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
};

const REGION_LABELS: Record<string, string> = {
  image_left_periocular: "รอบดวงตาด้านซ้ายของภาพ",
  image_right_periocular: "รอบดวงตาด้านขวาของภาพ",
};

const OUTDOOR_LABELS: Record<number, string> = {
  1: "ต่ำกว่า 1 ชั่วโมง",
  2: "1–น้อยกว่า 3 ชั่วโมง",
  3: "3–น้อยกว่า 4 ชั่วโมง",
  4: "4 ชั่วโมงขึ้นไป",
};

const REASON_LABELS: Record<string, string> = {
  reported_severe_irritation: "คุณรายงานการระคายเคืองรุนแรง",
  reported_allergy: "คุณรายงานประวัติการแพ้ผลิตภัณฑ์",
  reported_high_sensitivity: "คุณรายงานว่าผิวไวต่อการระคายเคืองสูง",
  no_supported_rule_inputs: "ข้อมูลที่บันทึกยังไม่ตรงกับกฎคำแนะนำที่มี",
  safety_screening_incomplete: "กรุณาบันทึกข้อมูลความไวต่อการระคายเคืองและประวัติแพ้ผลิตภัณฑ์ก่อน",
  analysis_not_complete: "ผลวิเคราะห์ภาพยังไม่เสร็จ",
  image_quality_below_threshold: "คุณภาพภาพไม่ผ่านเกณฑ์",
  wrinkle_confidence_not_released: "คะแนนริ้วรอยยังไม่ผ่านเกณฑ์ความเชื่อมั่นที่เผยแพร่",
  wrinkle_calibration_not_released: "ยังไม่มีการเผยแพร่การปรับเทียบคะแนนริ้วรอยนี้",
  wrinkle_provenance_incomplete: "ข้อมูลรุ่นของคะแนนริ้วรอยไม่ครบ",
  released_score_missing: "ไม่มีคะแนนริ้วรอยที่เผยแพร่สำหรับภาพนี้",
};

function formatThaiDate(value: string | undefined): string {
  if (!value) return "วันที่ไม่ระบุ";
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.valueOf()) ? value : new Intl.DateTimeFormat("th-TH", { day: "numeric", month: "short", year: "numeric" }).format(parsed);
}

export function RecommendationPanel() {
  const [data, setData] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/api/analysis/recommendations", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "โหลดคำแนะนำไม่สำเร็จ");
        return body as Result;
      })
      .then((result) => { if (active) setData(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "โหลดคำแนะนำไม่สำเร็จ"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) return <p role="status">กำลังโหลดคำแนะนำ…</p>;
  if (error) {
    return <div className="recommendation-card" role="status"><p>{error}</p>{error.includes("เข้าสู่ระบบ") && <Link className="text-button" href="/login">เข้าสู่ระบบ →</Link>}</div>;
  }
  if (!data) return <p role="status">ยังไม่มีข้อมูลคำแนะนำ</p>;

  return (
    <div aria-live="polite">
      {data.status === "safety_blocked" ? (
        <article className="recommendation-card recommendation-blocked"><span className="status">หยุดคำแนะนำเพื่อความปลอดภัย</span><h3>ต้องอัปเดตข้อมูลก่อน</h3><p>{REASON_LABELS[data.blocked_reason ?? ""] ?? "ข้อมูลที่รายงานต้องได้รับการพิจารณาก่อน"}</p><Link className="primary-button" href={data.questionnaire_context.status === "missing" ? "/onboarding/health" : "/onboarding/health?edit=1"}>{data.questionnaire_context.status === "missing" ? "เริ่มตอบแบบสอบถาม →" : "อัปเดตข้อมูลความปลอดภัย →"}</Link></article>
      ) : data.recommendations.length ? (
        <div className="recommendation-list">
          {data.recommendations.map((item) => (
            <article className="recommendation-card" key={item.rule_id}>
              <span className="status moderate">หมวดผลิตภัณฑ์</span>
              <h3>{item.category}</h3>
              <p>{item.rationale}</p>
              <div className="rule-box">
                <h3>ที่มาของคำแนะนำ</h3>
                <p>ข้อมูลที่ใช้: {item.signal_sources.map((source) => source === "image" ? "คะแนนจากภาพ" : source === "daily_health_reported" ? "Daily Health ที่คุณรายงาน" : "คุณรายงาน").join(" + ")}</p>
                {item.wrinkle_regions?.length ? <p>บริเวณคะแนนที่เผยแพร่: {item.wrinkle_regions.map((region) => REGION_LABELS[region] ?? region).join(", ")}</p> : null}
                {item.wrinkle_region_scores?.map((region) => <p key={region.region}>{REGION_LABELS[region.region] ?? region.region}: wrinkle score {region.score.toFixed(1)} / 100</p>)}
                <p className="metadata">กฎ {item.rule_id} · v{item.rule_version} · ฐานข้อมูล {item.knowledge_source.id} v{item.knowledge_source.version}</p>
                <p><a href={item.knowledge_source.reference.url} target="_blank" rel="noreferrer">{item.knowledge_source.reference.title} ↗</a></p>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <article className="recommendation-card recommendation-blocked"><span className="status">ยังไม่มีคำแนะนำ</span><h3>เริ่มจากข้อมูลที่มี</h3><p>{REASON_LABELS[data.blocked_reason ?? ""] ?? "ข้อมูลที่บันทึกยังไม่เพียงพอสำหรับกฎคำแนะนำ"}</p><Link className="primary-button" href={data.questionnaire_context.status === "missing" ? "/onboarding/health" : "/onboarding/health?edit=full"}>{data.questionnaire_context.status === "missing" ? "เริ่มตอบแบบสอบถาม →" : "แก้ไขข้อมูลผิวและการกันแดด →"}</Link></article>
      )}
      {(data.daily_context.reported_dryness || data.daily_context.lifestyle) && (
        <section className="recommendation-context" aria-label="ข้อมูลประกอบจาก Daily Health">
          <div className="recommendation-context-heading"><div><p className="eyebrow">ข้อมูลประกอบ</p><h3>Daily Health ที่คุณรายงาน</h3></div></div>
          <div className="recommendation-context-grid">
            {data.daily_context.reported_dryness && <div><span>ความแห้งผิว · {formatThaiDate(data.daily_context.reported_dryness.observed_date)}</span><strong>{data.daily_context.reported_dryness.value} <small>/ 10</small></strong></div>}
            {data.daily_context.lifestyle && <><div><span>การนอน · {formatThaiDate(data.daily_context.lifestyle.observed_date)}</span><strong>{data.daily_context.lifestyle.sleep_duration_minutes} <small>นาที</small></strong></div><div><span>น้ำ · {formatThaiDate(data.daily_context.lifestyle.observed_date)}</span><strong>{data.daily_context.lifestyle.water_intake_ml} <small>มล.</small></strong></div><div><span>กิจกรรมกลางแจ้ง · {formatThaiDate(data.daily_context.lifestyle.observed_date)}</span><strong><small>{OUTDOOR_LABELS[data.daily_context.lifestyle.outdoor_exposure_choice] ?? "ไม่ระบุ"}</small></strong></div></>}
          </div>
          <p>ใช้เฉพาะข้อมูลที่คุณรายงานเอง; ค่าคาดการณ์จากโมเดล Daily Health ไม่ถูกใช้เพื่อแนะนำผลิตภัณฑ์</p>
        </section>
      )}
      {data.image_context.status !== "eligible" && (
        <p className="recommendation-note">คะแนนจากภาพไม่ได้ถูกใช้: {REASON_LABELS[data.image_context.reason ?? ""] ?? "คะแนนภาพไม่พร้อมใช้งาน"}</p>
      )}
      <p className="metadata">กฎคำแนะนำ v{data.rule_version}{data.image_context.score_version ? ` · score ${data.image_context.score_version}` : ""}{data.image_context.calibration_version ? ` · calibration ${data.image_context.calibration_version}` : ""}</p>
      <p className="recommendation-warning">{data.disclaimer}</p>
    </div>
  );
}
