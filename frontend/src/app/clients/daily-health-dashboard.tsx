import type { PredictionResponse } from "@/lib/daily-health-types";
import DailyHealthRiskResults from "./daily-health-risk-results";
import { useLanguage } from "@/components/language-provider";

export default function DailyHealthDashboard({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  const { language } = useLanguage();
  const profileMessages = new Set(
    prediction.interpretation.profile_guidance.map((item) => item.message),
  );
  const recommendations = [...new Set(prediction.guidance)].filter(
    (item) => !profileMessages.has(item),
  );

  return (
    <section className="daily-health-dashboard personalized-guidance" aria-label={language === "en" ? "Daily health risk results" : "ผลความเสี่ยงสุขภาพรายวัน"} aria-live="polite">
      <div>
        <p className="eyebrow">DAILY HEALTH SIGNALS</p>
        <h2>{language === "en" ? "Health risks and signals" : "ความเสี่ยงและสัญญาณสุขภาพ"}</h2>
      </div>
      <DailyHealthRiskResults interpretation={prediction.interpretation} />
      {recommendations.length > 0 ? (
        <section className="personalized-guidance" aria-label={language === "en" ? "Today's guidance" : "คำแนะนำสำหรับวันนี้"}>
          <h3>{language === "en" ? "Today's guidance" : "คำแนะนำสำหรับวันนี้"}</h3>
          {language === "en" && <p lang="en">Personalized guidance is currently available in Thai.</p>}
          <ul className="personalized-guidance-list" lang={language === "en" ? "th" : undefined}>
            {recommendations.map((recommendation) => (
              <li key={recommendation}>{recommendation}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
