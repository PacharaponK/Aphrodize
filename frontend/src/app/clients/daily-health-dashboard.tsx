import type { DailyHealthInterpretation } from "@/lib/daily-health-types";
import DailyHealthRiskResults from "./daily-health-risk-results";
import { useLanguage } from "@/components/language-provider";

export default function DailyHealthDashboard({
  interpretation, date, guidance = [], modelId,
}: {
  interpretation: DailyHealthInterpretation;
  date: string;
  guidance?: string[];
  modelId?: string | null;
}) {
  const { language } = useLanguage();

  return (
    <section className="daily-health-dashboard" aria-label={language === "en" ? "Daily health risk results" : "ผลความเสี่ยงสุขภาพรายวัน"} aria-live="polite">
      <div>
        <p className="eyebrow">{language === "en" ? "DAILY HEALTH SIGNALS" : "สัญญาณสุขภาพรายวัน"}</p>
        <h2>{language === "en" ? "Health risks and signals" : "ความเสี่ยงและสัญญาณสุขภาพ"}</h2>
      </div>
      <DailyHealthRiskResults interpretation={interpretation} date={date} guidance={guidance} modelId={modelId} />
    </section>
  );
}
