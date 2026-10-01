import { pageMetadata } from "@/lib/page-metadata";
import DailyHealthHistoryPanel from "../clients/daily-health-history-panel";
import { LocalizedText } from "@/components/language-provider";
import "../clients/clients.css";
import "../clients/daily-health-history.css";

export const metadata = pageMetadata(
  "Trends",
  "Explore your daily health history, recorded habits and experimental wellness signals over time. Review contributing factors and guidance without treating estimates as a diagnosis.",
  "/trend",
  false,
  "en_US",
);

export default function Page() {
  return (
    <>
      <div className="simple-page clients-page trend-page">
      <main className="page-frame">
        <section className="page-content clients-content">
          <p className="eyebrow">DAILY HEALTH TRENDS</p>
          <h1><LocalizedText th="แนวโน้มความเสี่ยงสุขภาพ" en="Daily health trends" /></h1>
          <p className="clients-intro">
            <LocalizedText th="ดูระดับสัญญาณสุขภาพ คำแนะนำ และปัจจัยรายวันจากข้อมูลที่บันทึกไว้ โดยไม่ใช้ผลประเมินแทนการวินิจฉัย" en="Review daily signals, guidance and contributing factors from your records. These estimates are not a diagnosis." />
          </p>
          <DailyHealthHistoryPanel view="trend" />
        </section>
      </main>
    </div>
    </>
  );
}
