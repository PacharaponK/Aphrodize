import type { Metadata } from "next";
import DailyHealthHistoryPanel from "../clients/daily-health-history-panel";
import { AppNavigation } from "@/components/app-navigation";
import "../clients/clients.css";
import "../clients/daily-health-history.css";

export const metadata: Metadata = {
  title: "แนวโน้มความเสี่ยงสุขภาพ — Aphrodize",
  description: "ติดตามสัญญาณความเสี่ยงสุขภาพรายวันจากข้อมูลที่บันทึกไว้",
};

export default function Page() {
  return (
    <>
      <AppNavigation active="trend" showThemeToggle />
      <div className="simple-page clients-page trend-page">
      <main className="page-frame">
        <section className="page-content clients-content">
          <p className="eyebrow">DAILY HEALTH TRENDS</p>
          <h1>แนวโน้มความเสี่ยงสุขภาพ</h1>
          <p className="clients-intro">
            ดูระดับสัญญาณสุขภาพ คำแนะนำ และปัจจัยรายวันจากข้อมูลที่บันทึกไว้ โดยไม่ใช้ผลประเมินแทนการวินิจฉัย
          </p>
          <DailyHealthHistoryPanel view="trend" />
        </section>
      </main>
    </div>
    </>
  );
}
