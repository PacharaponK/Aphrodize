"use client";

import type { DailyHealthInterpretation, HealthSignal } from "@/lib/daily-health-types";
import { useLanguage } from "@/components/language-provider";

const riskSignals = (interpretation: DailyHealthInterpretation, language: "th" | "en") => [
  { label: language === "en" ? "Overall wellness" : "สุขภาพโดยรวม", signal: interpretation.daily_health_summary },
  { label: language === "en" ? "Dryness and skin care" : "ผิวแห้งและการดูแลผิว", signal: interpretation.skin_care_attention_level },
  { label: language === "en" ? "Acne signal" : "สัญญาณสิว", signal: interpretation.acne_flare_signal },
  { label: language === "en" ? "Next-day energy" : "พลังงานวันถัดไป", signal: interpretation.next_day_predictions.low_energy_signal },
  { label: language === "en" ? "Next-day thirst" : "กระหายน้ำวันถัดไป", signal: interpretation.next_day_predictions.thirst_attention },
];

function levelLabel(signal: HealthSignal, language: "th" | "en"): string {
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

function unavailableMessage(signal: HealthSignal, language: "th" | "en"): string {
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
  const hasForecast = signal.status === "predicted" && typeof signal.value_0_10 === "number"
    && Number.isFinite(signal.value_0_10) && signal.value_0_10 >= 0 && signal.value_0_10 <= 10;
  const signalClass = hasLevel ? ` health-signal-${signal.level}` : " health-signal-unrated";

  return (
    <article className={`health-signal-card${signalClass}`}>
      <div className="health-signal-heading">
        <h3>{label}</h3>
        <span className="health-signal-level">{levelLabel(signal, language)}</span>
      </div>
      {hasForecast ? <div className="health-signal-forecast">
        <p className="health-signal-headline"><strong>{signal.value_0_10} / 10</strong></p>
        <p className="health-signal-note">{language === "en" ? "For" : "สำหรับวันที่"} <time dateTime={signal.target_date}>{signal.target_date}</time></p>
        <p className="health-signal-note">{signal.target === "perceived_energy"
          ? language === "en" ? "Estimated perceived energy; higher means more energy." : "ค่าประมาณพลังงานที่รู้สึก ค่าสูงหมายถึงมีพลังงานมากขึ้น"
          : language === "en" ? "Estimated perceived thirst, not the weight-based water formula." : "ค่าประมาณความกระหายที่รู้สึก ไม่ใช่สูตรน้ำดื่มตามน้ำหนัก"}</p>
        <p className="health-signal-note">{language === "en" ? "Model" : "โมเดล"}: {signal.model_id}</p>
      </div> : null}
      {signal.headline ? <p className="health-signal-headline" lang={language === "en" ? "th" : undefined}>{signal.headline}</p> : null}
      {signal.possible_signals?.length ? (
        <p className="health-signal-possibilities" lang={language === "en" ? "th" : undefined}>{signal.possible_signals.join(" · ")}</p>
      ) : null}
      {!hasLevel && !hasForecast && !signal.headline && !signal.possible_signals?.length ? (
        <p className="health-signal-note">{unavailableMessage(signal, language)}</p>
      ) : null}
      {signal.status === "model_not_ready" ? <a className="text-button" href="/clients#daily-outcome-title">{language === "en" ? "Record observed outcomes" : "บันทึกผลที่สังเกตจริง"}</a> : null}
      {signal.recommendations?.length ? (
        <ul className="health-signal-recommendations">
          {signal.recommendations.map((recommendation) => (
            <li key={recommendation} lang={language === "en" ? "th" : undefined}>{recommendation}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

export default function DailyHealthRiskResults({
  interpretation,
}: {
  interpretation: DailyHealthInterpretation;
}) {
  const { language } = useLanguage();
  return (
    <div className="daily-risk-results">
      <div className="daily-risk-grid" aria-label={language === "en" ? "Risk levels and wellness signals" : "ระดับความเสี่ยงและสัญญาณสุขภาพ"}>
        {riskSignals(interpretation, language).map(({ label, signal }) => (
          <RiskCard key={label} label={label} signal={signal} language={language} />
        ))}
      </div>
      {interpretation.profile_guidance.length > 0 ? (
        <section className="profile-guidance daily-risk-profile-guidance" aria-label={language === "en" ? "Personalized guidance" : "คำแนะนำตามข้อมูลส่วนตัว"}>
          <h3>{language === "en" ? "Guidance based on your profile" : "คำแนะนำที่ปรับตามข้อมูลส่วนตัว"}</h3>
          <ul>
            {interpretation.profile_guidance.map(({ topic, message, reference_url, reference_label }) => (
              <li key={topic}>
                <span lang={language === "en" ? "th" : undefined}>{message}</span>
                {reference_url ? (
                  <> <a href={reference_url} target="_blank" rel="noreferrer" lang={language === "en" ? "th" : undefined}>{reference_label ?? (language === "en" ? "Source" : "แหล่งข้อมูล")}</a></>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <p className="daily-risk-disclaimer">{language === "en" ? "Signals from your health records—not a diagnosis." : "สัญญาณจากบันทึกสุขภาพ ไม่ใช่การวินิจฉัย"}</p>
    </div>
  );
}
