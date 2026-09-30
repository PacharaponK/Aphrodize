import type { Metadata } from "next";
import { connection } from "next/server";
import DailyHealthTracker from "./daily-health-tracker";
import { AppNavigation } from "@/components/app-navigation";
import { LocalizedText } from "@/components/language-provider";
import "./clients.css";
import { todayInBangkok } from "@/lib/daily-health-prediction";

export const metadata: Metadata = {
  title: "บันทึกสุขภาพรายวัน — Aphrodize",
  description: "บันทึกการนอน น้ำดื่ม และเวลาอยู่นอกบ้าน",
};

export default async function ClientsPage() {
  await connection();
  const initialDate = todayInBangkok();
  return (
    <>
      <AppNavigation active="clients" showThemeToggle />
      <div className="simple-page clients-page">
      <main className="page-frame">
        <section className="page-content clients-content">
          <p className="eyebrow">DAILY HEALTH TRACKER</p>
          <h1><LocalizedText th="ติดตามสุขภาพและสภาพผิว" en="Daily health and skin tracking" /></h1>
          <p className="clients-intro">
            <LocalizedText th="บันทึกการนอน ปริมาณน้ำดื่ม และเวลาอยู่นอกบ้าน เพื่อเรียกโมเดลทดลองประเมินคะแนนและแสดงข้อแนะนำที่เกี่ยวข้อง" en="Record sleep, water intake and time outdoors to receive experimental scores and relevant guidance." />
          </p>
          <DailyHealthTracker initialDate={initialDate} />
        </section>
      </main>
    </div>
    </>
  );
}
