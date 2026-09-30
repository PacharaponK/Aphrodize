import type { Metadata } from "next";
import DailyHealthHistoryPanel from "../clients/daily-health-history-panel";
import { LocalizedText } from "@/components/language-provider";
import "../clients/clients.css";
import "../clients/daily-health-history.css";

export const metadata: Metadata = {
  title: "แนวโน้มความเสี่ยงสุขภาพ — Aphrodize",
  description: "ติดตามสัญญาณความเสี่ยงสุขภาพรายวันจากข้อมูลที่บันทึกไว้",
};

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
