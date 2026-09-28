import type { PredictionResponse } from "@/lib/daily-health-types";
import DailyHealthRiskResults from "./daily-health-risk-results";

export default function DailyHealthDashboard({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  const profileMessages = new Set(
    prediction.interpretation.profile_guidance.map((item) => item.message),
  );
  const recommendations = [...new Set(prediction.guidance)].filter(
    (item) => !profileMessages.has(item),
  );

  return (
    <section className="daily-health-dashboard personalized-guidance" aria-label="ผลความเสี่ยงสุขภาพรายวัน" aria-live="polite">
      <div>
        <p className="eyebrow">DAILY HEALTH SIGNALS</p>
        <h2>ความเสี่ยงและสัญญาณสุขภาพ</h2>
      </div>
      <DailyHealthRiskResults interpretation={prediction.interpretation} />
      {recommendations.length > 0 ? (
        <section className="personalized-guidance" aria-label="คำแนะนำสำหรับวันนี้">
          <h3>คำแนะนำสำหรับวันนี้</h3>
          <ul className="personalized-guidance-list">
            {recommendations.map((recommendation) => (
              <li key={recommendation}>{recommendation}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
