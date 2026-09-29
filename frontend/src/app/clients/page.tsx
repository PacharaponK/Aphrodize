import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import DailyHealthTracker from "./daily-health-tracker";
import { AppNavigation } from "@/components/app-navigation";
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
          <h1>ติดตามสุขภาพและสภาพผิว</h1>
          <p className="clients-intro">
            บันทึกการนอน ปริมาณน้ำดื่ม และเวลาอยู่นอกบ้าน เพื่อเรียกโมเดลทดลองประเมินคะแนนและแสดงข้อแนะนำที่เกี่ยวข้อง
          </p>
          <div className="page-actions clients-test-actions">
            <Link className="secondary-button" href="/clients/test">เปิดหน้าแบบฟอร์มทดสอบโมเดล</Link>
          </div>
          <DailyHealthTracker initialDate={initialDate} />
        </section>
      </main>
    </div>
    </>
  );
}
