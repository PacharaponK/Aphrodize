"use client";

import type { DailyHealthInterpretation, HealthSignal } from "@/lib/daily-health-types";
import { useLanguage } from "@/components/language-provider";
const riskSignals = (interpretation: DailyHealthInterpretation, language: "th" | "en") => [
  { id: "wellness", label: language === "en" ? "Overall wellness" : "สุขภาพโดยรวม", signal: interpretation.daily_health_summary },
  { id: "dryness", label: language === "en" ? "Dryness and skin care" : "ผิวแห้งและการดูแลผิว", signal: interpretation.skin_care_attention_level },
  { id: "energy", label: language === "en" ? "Next-day energy" : "พลังงานวันถัดไป", signal: interpretation.next_day_predictions.low_energy_signal },
  { id: "thirst", label: language === "en" ? "Next-day thirst" : "กระหายน้ำวันถัดไป", signal: interpretation.next_day_predictions.thirst_attention },
];

export const validForecast = (signal: HealthSignal) => signal.status === "predicted"
  && typeof signal.value_0_10 === "number" && Number.isFinite(signal.value_0_10)
  && signal.value_0_10 >= 0 && signal.value_0_10 <= 10;

export function levelLabel(signal: HealthSignal, language: "th" | "en"): string {
  if (signal.level === "low") return language === "en" ? "Low" : "ต่ำ";
  if (signal.level === "moderate") return language === "en" ? "Moderate" : "ปานกลาง";
  if (signal.level === "high") return language === "en" ? "High" : "สูง";

  switch (signal.status) {
    case "predicted": return language === "en" ? "Experimental estimate" : "ค่าประมาณทดลอง";
    case "not_supported": return language === "en" ? "Not supported yet" : "ยังไม่รองรับ";
    case "model_not_ready": return language === "en" ? "Model not ready" : "โมเดลยังไม่พร้อม";
    case "out_of_training_domain": return language === "en" ? "Not assessed" : "งดประเมิน";
    case "insufficient_data": return language === "en" ? "Insufficient data" : "ข้อมูลไม่พอ";
    case "insufficient_history": return language === "en" ? "Insufficient history" : "ข้อมูลย้อนหลังไม่พอ";
    default: return language === "en" ? "Unavailable" : "ยังไม่มีผล";
  }
}

export function unavailableMessage(signal: HealthSignal, language: "th" | "en"): string {
  switch (signal.status) {
    case "not_supported":
      return language === "en" ? "This assessment is not implemented yet." : "ยังไม่มีระบบประเมินสัญญาณนี้";
    case "model_not_ready":
      return language === "en" ? "No approved model trained on observed outcomes is available for this signal." : "ยังไม่มีโมเดลจากผลที่ผู้ใช้รายงานจริงที่ผ่านการอนุมัติสำหรับสัญญาณนี้";
    case "out_of_training_domain":
      return signal.headline ?? (language === "en" ? "A risk level is not shown for this input." : "ยังไม่แสดงระดับความเสี่ยงสำหรับข้อมูลชุดนี้");
    case "insufficient_data":
      return language === "en" ? "Not enough self-reported data yet." : "ข้อมูลที่ผู้ใช้รายงานยังไม่พอ";
    case "insufficient_history":
      return language === "en" ? "Not enough self-reported outcome history yet." : "ประวัติผลที่ผู้ใช้รายงานยังไม่พอ";
    default:
      return language === "en" ? "No assessment is available for this item." : "ไม่มีผลประเมินสำหรับรายการนี้";
  }
}

function RiskCard({ label, signal, language }: { label: string; signal: HealthSignal; language: "th" | "en" }) {
  const hasLevel = signal.level !== null;
  const hasForecast = validForecast(signal);
  const signalClass = hasLevel ? ` health-signal-${signal.level}` : " health-signal-unrated";

  return (
    <article className={`health-signal-card${signalClass}`}>
      <div className="health-signal-heading">
        <h4>{label}</h4>
        <span className="health-signal-level">{levelLabel(signal, language)}</span>
      </div>
      {hasForecast ? <div className="health-signal-forecast">
        <p className="health-signal-headline"><strong>{signal.value_0_10} / 10</strong></p>
        <p className="health-signal-note">{language === "en" ? "For" : "สำหรับวันที่"} <time dateTime={signal.target_date}>{signal.target_date}</time></p>
        <p className="health-signal-note">{signal.target === "perceived_energy"
          ? language === "en" ? "Estimated perceived energy; higher means more energy." : "ค่าประมาณพลังงานที่รู้สึก ค่าสูงหมายถึงมีพลังงานมากขึ้น"
          : language === "en" ? "Estimated perceived thirst, not the weight-based water formula." : "ค่าประมาณความกระหายที่รู้สึก ไม่ใช่สูตรน้ำดื่มตามน้ำหนัก"}</p>
      </div> : null}
      {signal.headline ? <p className="health-signal-headline" lang={language === "en" ? "th" : undefined}>{signal.headline}</p> : null}
      {signal.possible_signals?.length ? (
        <p className="health-signal-possibilities" lang={language === "en" ? "th" : undefined}>{signal.possible_signals.join(" · ")}</p>
      ) : null}
      {!hasLevel && !hasForecast && !signal.headline && !signal.possible_signals?.length ? (
        <p className="health-signal-note">{unavailableMessage(signal, language)}</p>
      ) : null}
    </article>
  );
}

export default function DailyHealthRiskResults({
  interpretation, date, guidance = [], modelId,
}: {
  interpretation: DailyHealthInterpretation;
  date?: string;
  guidance?: string[];
  modelId?: string | null;
}) {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "th" ? th : en;
  const signals = riskSignals(interpretation, language);
  const forecasts = signals.slice(2);
  const unavailable = forecasts.filter(({ signal }) => !validForecast(signal));
  const messages = [...new Set([
    ...signals.flatMap(({ signal }) => signal.recommendations ?? []),
    ...interpretation.profile_guidance.map(({ message }) => message),
    ...guidance,
  ].filter(Boolean))];
  return (
    <div className="daily-risk-results">
      <section className="daily-risk-current" aria-label={t("จากบันทึกของคุณ", "Your recorded day")}>
        <h3>{t("จากบันทึกของคุณ", "Your recorded day")}{date ? <> · <time dateTime={date}>{date}</time></> : null}</h3>
        <div className="daily-risk-grid">
          {signals.slice(0, 2).map(({ id, label, signal }) => (
            <RiskCard key={id} label={label} signal={signal} language={language} />
          ))}
        </div>
      </section>
      <section className="daily-risk-outlook" aria-label={t("แนวโน้มวันถัดไป", "Next-day outlook")}>
        <h3>{t("แนวโน้มวันถัดไป", "Next-day outlook")}</h3>
        {forecasts.some(({ signal }) => validForecast(signal)) ? <div className="daily-risk-grid">
          {forecasts.filter(({ signal }) => validForecast(signal)).map(({ id, label, signal }) => <RiskCard key={id} label={label} signal={signal} language={language} />)}
        </div> : null}
        {unavailable.length ? <div className="daily-risk-unavailable">
          <dl>{unavailable.map(({ id, label, signal }) => <div key={id}>
            <dt>{label}</dt><dd>{signal.status === "predicted" ? t("ยังไม่มีผล", "Unavailable") : levelLabel(signal, language)}</dd>
            <dd className="health-signal-note">{unavailableMessage(signal, language)}</dd>
            {signal.headline && signal.status !== "out_of_training_domain" ? <dd lang="th">{signal.headline}</dd> : null}
            {signal.possible_signals?.length ? <dd lang="th">{signal.possible_signals.join(" · ")}</dd> : null}
          </div>)}</dl>
          {unavailable.some(({ signal }) => signal.status === "model_not_ready") ? <p className="health-signal-note">{t("การบันทึกผลจริงไม่ทำให้โมเดลเปิดใช้งานทันที ต้องผ่านการตรวจสอบและอนุมัติก่อน", "Recording outcomes does not activate a model immediately; review and approval are still required.")}</p> : null}
          {unavailable.some(({ signal }) => ["model_not_ready", "insufficient_data", "insufficient_history"].includes(signal.status)) ? <a className="text-button" href="/clients#daily-outcome-title">{t("บันทึกผลที่สังเกตจริง", "Record observed outcomes")}</a> : null}
        </div> : null}
      </section>
      {messages.length ? <details className="daily-risk-guidance">
        <summary>{t("คำแนะนำและเหตุผล", "Guidance & context")}</summary>
        {language === "en" ? <p className="health-signal-note">Guidance is shown in its original Thai.</p> : null}
        <ul>{messages.map(message => <li key={message} lang="th">{message}
          {interpretation.profile_guidance.filter(item => item.message === message && item.reference_url).map(item => <span key={item.topic}> <a href={item.reference_url} target="_blank" rel="noreferrer">{item.reference_label ?? t("แหล่งข้อมูล", "Source")}</a></span>)}
        </li>)}</ul>
      </details> : null}
      {modelId || signals.some(({ signal }) => signal.model_id || signal.method || signal.drivers?.length || signal.reason_codes?.length) ? <details className="daily-risk-provenance">
        <summary>{t("วิธีประเมินและที่มาของผล", "Assessment method & provenance")}</summary>
        {modelId ? <p className="health-signal-note">{t("โมเดลของคะแนน", "Score model")}: {modelId}</p> : null}
        <dl>{signals.filter(({ signal }) => signal.model_id || signal.method || signal.drivers?.length || signal.reason_codes?.length).map(({ id, label, signal }) => <div key={id}>
          <dt>{label}</dt>{signal.model_id ? <dd>{signal.model_id}</dd> : null}{signal.method ? <dd>{signal.method}</dd> : null}
          {[...new Set([...(signal.drivers ?? []), ...(signal.reason_codes ?? [])])].map(reason => <dd key={reason}>{reason}</dd>)}
        </div>)}</dl>
      </details> : null}
      <p className="daily-risk-disclaimer">{language === "en" ? "Signals from your health records—not a diagnosis." : "สัญญาณจากบันทึกสุขภาพ ไม่ใช่การวินิจฉัย"}</p>
    </div>
  );
}
