import { pageMetadata } from "@/lib/page-metadata";
import { connection } from "next/server";
import DailyHealthTracker from "./daily-health-tracker";
import { LocalizedText } from "@/components/language-provider";
import "./clients.css";
import { todayInBangkok } from "@/lib/daily-health-prediction";

export const metadata = pageMetadata(
  "Health log",
  "Record sleep, water intake and time outdoors to track daily wellness and receive experimental insights. These estimates are not a medical diagnosis.",
  "/clients",
  false,
  "en_US",
);

export default async function ClientsPage() {
  await connection();
  const initialDate = todayInBangkok();
  return (
    <>
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
