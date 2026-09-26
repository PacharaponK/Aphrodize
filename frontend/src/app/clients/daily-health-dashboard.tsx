import type { HealthSignal, PredictionResponse } from "@/lib/daily-health-types";

const levelLabels = {
  low: "ต่ำ",
  moderate: "กลาง",
  high: "สูง",
} as const;

const reasonLabels: Record<string, string> = {
  sleep_below_6_hours: "เวลานอนต่ำกว่า 6 ชั่วโมง",
  sleep_below_7_hours: "เวลานอนต่ำกว่า 7 ชั่วโมง",
  thirst_signal_elevated: "คะแนนสัญญาณกระหายน้ำอยู่ระดับกลางขึ้นไป",
  dryness_signal_elevated: "คะแนนสัญญาณผิวแห้งอยู่ระดับกลางขึ้นไป",
  model_input_outside_training_domain: "ข้อมูลอยู่นอกช่วงฝึกของโมเดล",
  sleep_duration_outside_training_range: "เวลานอนอยู่นอกช่วงที่โมเดลฝึกมา",
  water_intake_outside_training_range: "ปริมาณน้ำอยู่นอกช่วงที่โมเดลฝึกมา",
};

function SignalCard({ title, signal }: { title: string; signal: HealthSignal }) {
  const label = signal.level ? levelLabels[signal.level] : null;
  const available = signal.status === "available";

  return (
    <article className={"health-signal-card" + (label ? " health-signal-" + signal.level : "")}>
      <div className="health-signal-heading">
        <h3>{title}</h3>
        <span className="health-signal-level">
          {label ?? (signal.status === "out_of_training_domain" ? "ประเมินไม่ได้" : "ข้อมูลไม่พอ")}
        </span>
      </div>
      {signal.headline && <p className="health-signal-headline">{signal.headline}</p>}
      {!available && signal.status === "out_of_training_domain" && signal.drivers && signal.drivers.length > 0 && (
        <p className="health-signal-reasons">
          นอกช่วงฝึก: {signal.drivers.map((reason) => reasonLabels[reason] ?? reason).join(" · ")}
        </p>
      )}
      {available && signal.drivers && signal.drivers.length > 0 && (
        <p className="health-signal-reasons">
          อ้างอิงจาก: {signal.drivers.map((reason) => reasonLabels[reason] ?? reason).join(" · ")}
        </p>
      )}
      {available && signal.possible_signals && signal.possible_signals.length > 0 && (
        <p className="health-signal-possibilities">
          อาจสังเกตได้: {signal.possible_signals.join(" · ")}
        </p>
      )}
      {available && signal.recommendations && signal.recommendations.length > 0 && (
        <ul className="health-signal-recommendations">
          {signal.recommendations.map((recommendation) => (
            <li key={recommendation}>{recommendation}</li>
          ))}
        </ul>
      )}
      {!available && signal.status === "out_of_training_domain" && (
        <p className="health-signal-note">ระบบงดสรุปความเสี่ยงจากข้อมูลชุดนี้ เพื่อไม่คาดเดานอกช่วงที่ตรวจสอบแล้ว</p>
      )}
      {!available && signal.status !== "out_of_training_domain" && (
        <p className="health-signal-note">ยังไม่มีข้อมูลเพียงพอสำหรับประเมินส่วนนี้</p>
      )}
    </article>
  );
}

export default function DailyHealthDashboard({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  const { interpretation } = prediction;
  const nextDay = interpretation.next_day_predictions;

  return (
    <section className="daily-health-dashboard" aria-labelledby="daily-health-dashboard-title" aria-live="polite">
      <div className="daily-health-dashboard-heading">
        <div>
          <p className="eyebrow">DAILY WELLNESS SUMMARY</p>
          <h2 id="daily-health-dashboard-title">ภาพรวมสุขภาวะรายวัน</h2>
        </div>
        <p>ระดับจากกฎทดลองและข้อมูลที่กรอก ไม่ใช่เปอร์เซ็นต์ความเสี่ยงหรือการวินิจฉัย</p>
      </div>

      <SignalCard title="สัญญาณที่ควรใส่ใจวันนี้" signal={interpretation.daily_health_summary} />
      <SignalCard title="การใส่ใจผิว" signal={interpretation.skin_care_attention_level} />

      {interpretation.profile_guidance.length > 0 && (
        <section className="profile-guidance" aria-labelledby="profile-guidance-title">
          <h3 id="profile-guidance-title">คำแนะนำจากข้อมูลที่คุณเลือกแชร์</h3>
          {interpretation.profile_guidance.map((item) => (
            <p key={item.topic}>{item.message}</p>
          ))}
        </section>
      )}

      <div className="next-day-statuses" aria-label="สถานะผลพยากรณ์วันถัดไป">
        <h3>แนวโน้มวันถัดไป</h3>
        <p>
          พลังงาน: {nextDay.low_energy_signal.status === "insufficient_history"
            ? "ยังไม่มีข้อมูลรายงานจริงเพียงพอ"
            : levelLabels[nextDay.low_energy_signal.level ?? "low"]}
        </p>
        <p>
          ความกระหายน้ำ: {nextDay.thirst_attention.status === "insufficient_history"
            ? "ยังไม่มีข้อมูลรายงานจริงเพียงพอ"
            : levelLabels[nextDay.thirst_attention.level ?? "low"]}
        </p>
      </div>
    </section>
  );
}
