import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { connection } from "next/server";
import DailyHealthTracker from "./daily-health-tracker";
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
    <div className="simple-page clients-page">
      <main className="page-frame">
        <header className="page-header">
          <Link className="page-brand" href="/">
            <Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />
            Aphrodize
          </Link>
          <nav className="page-nav" aria-label="เมนูหลัก">
            <Link href="/">ภาพรวม</Link>
            <Link href="/capture">วิเคราะห์ภาพ</Link>
            <Link href="/trend">แนวโน้ม</Link>
            <Link className="active" href="/clients" aria-current="page">สุขภาพรายวัน</Link>
            <Link href="/profile">Skin profile</Link>
          </nav>
        </header>

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
  );
}
