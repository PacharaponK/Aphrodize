import type { DailyHealthInterpretation, HealthSignal } from "@/lib/daily-health-types";

const riskSignals = (interpretation: DailyHealthInterpretation) => [
  { label: "สุขภาพโดยรวม", signal: interpretation.daily_health_summary },
  { label: "ผิวแห้งและการดูแลผิว", signal: interpretation.skin_care_attention_level },
  { label: "สัญญาณสิว", signal: interpretation.acne_flare_signal },
  { label: "พลังงานวันถัดไป", signal: interpretation.next_day_predictions.low_energy_signal },
  { label: "กระหายน้ำวันถัดไป", signal: interpretation.next_day_predictions.thirst_attention },
];

function levelLabel(signal: HealthSignal): string {
  if (signal.level === "low") return "ต่ำ";
  if (signal.level === "moderate") return "ปานกลาง";
  if (signal.level === "high") return "สูง";

  switch (signal.status) {
    case "out_of_training_domain": return "งดประเมิน";
    case "insufficient_data": return "ข้อมูลไม่พอ";
    case "insufficient_history": return "ข้อมูลย้อนหลังไม่พอ";
    default: return "ยังไม่มีผล";
  }
}

function unavailableMessage(signal: HealthSignal): string {
  switch (signal.status) {
    case "out_of_training_domain":
      return signal.headline ?? "ยังไม่แสดงระดับความเสี่ยงสำหรับข้อมูลชุดนี้";
    case "insufficient_data":
      return "ยังไม่มีข้อมูลที่สังเกตจริงเพียงพอสำหรับสัญญาณนี้";
    case "insufficient_history":
      return "ยังไม่มีประวัติผลที่ผู้ใช้รายงานจริงเพียงพอสำหรับการประเมิน";
    default:
      return "ไม่มีผลประเมินสำหรับรายการนี้";
  }
}

function RiskCard({ label, signal }: { label: string; signal: HealthSignal }) {
  const hasLevel = signal.level !== null;
  const signalClass = hasLevel ? ` health-signal-${signal.level}` : " health-signal-unrated";

  return (
    <article className={`health-signal-card${signalClass}`}>
      <div className="health-signal-heading">
        <h3>{label}</h3>
        <span className="health-signal-level">{levelLabel(signal)}</span>
      </div>
      {signal.headline ? <p className="health-signal-headline">{signal.headline}</p> : null}
      {signal.possible_signals?.length ? (
        <p className="health-signal-possibilities">{signal.possible_signals.join(" · ")}</p>
      ) : null}
      {!hasLevel && !signal.headline && !signal.possible_signals?.length ? (
        <p className="health-signal-note">{unavailableMessage(signal)}</p>
      ) : null}
      {signal.recommendations?.length ? (
        <ul className="health-signal-recommendations">
          {signal.recommendations.map((recommendation) => (
            <li key={recommendation}>{recommendation}</li>
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
  return (
    <div className="daily-risk-results">
      <div className="daily-risk-grid" aria-label="ระดับความเสี่ยงและสัญญาณสุขภาพ">
        {riskSignals(interpretation).map(({ label, signal }) => (
          <RiskCard key={label} label={label} signal={signal} />
        ))}
      </div>
      {interpretation.profile_guidance.length > 0 ? (
        <section className="profile-guidance daily-risk-profile-guidance" aria-label="คำแนะนำตามข้อมูลส่วนตัว">
          <h3>คำแนะนำที่ปรับตามข้อมูลส่วนตัว</h3>
          <ul>
            {interpretation.profile_guidance.map(({ topic, message, reference_url, reference_label }) => (
              <li key={topic}>
                {message}
                {reference_url ? (
                  <> <a href={reference_url} target="_blank" rel="noreferrer">{reference_label ?? "แหล่งข้อมูล"}</a></>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <p className="daily-risk-disclaimer">ผลเหล่านี้เป็นสัญญาณจากข้อมูลสุขภาพที่บันทึก ไม่ใช่การวินิจฉัยโรค</p>
    </div>
  );
}
