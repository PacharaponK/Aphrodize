import { pageMetadata } from "@/lib/page-metadata";
import { LocalizedText } from "../components/language-provider";
import { HomeHero } from "../components/home-hero";
import { HomeScrollMotion } from "../components/home-scroll-motion";
import DailyHealthHistoryPanel from "./clients/daily-health-history-panel";
import "./clients/clients.css";
import "./clients/daily-health-history.css";
import "./home.css";

export const metadata = pageMetadata(
  "Dashboard",
  "Review your skin observations, sleep, hydration and daily health records in one place. Plan your next check-in with Aphrodize.",
  "/",
  false,
  "en_US",
);

export default function Page() {
  return (
    <div className="app-shell home-dashboard-shell">
      <HomeScrollMotion />
      <main id="dashboard">
        <HomeHero />
        <section id="daily" className="home-dashboard-grid" aria-labelledby="home-daily-heading">
          <header className="home-daily-heading"><h2 id="home-daily-heading"><LocalizedText th="ความสม่ำเสมอเล็ก ๆ ในทุกวัน" en="A little consistency." /></h2><p><LocalizedText th="รวมบันทึกประจำวันของคุณไว้ด้วยกัน" en="Your daily records, brought together." /></p></header>
          <DailyHealthHistoryPanel view="dashboard" />
        </section>
        <p className="home-safety-note"><LocalizedText th="คะแนนและสัญญาณมีไว้เพื่อการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์" en="Scores and signals support personal tracking; they are not a medical diagnosis." /></p>
      </main>
    </div>
  );
}



