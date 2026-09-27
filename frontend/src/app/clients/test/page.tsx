import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { connection } from "next/server";
import { todayInBangkok } from "@/lib/daily-health-prediction";
import PredictionTestForm from "./prediction-test-form";
import "../clients.css";
import "./test.css";

export const metadata: Metadata = {
  title: "ทดสอบโมเดลสุขภาพรายวัน — Aphrodize",
  description: "ทดลองป้อนข้อมูลเพื่อทดสอบผลทำนายจากโมเดลสุขภาพรายวัน",
};

export default async function ClientsPredictionTestPage() {
  await connection();
  const initialDate = todayInBangkok();

  return (
    <div className="simple-page clients-page clients-test-page">
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
            <Link href="/clients">สุขภาพรายวัน</Link>
            <Link className="active" href="/clients/test" aria-current="page">ทดสอบโมเดล</Link>
            <Link href="/profile">Skin profile</Link>
          </nav>
        </header>

        <section className="page-content clients-content">
          <Link className="prediction-test-back-link" href="/clients">← กลับไปสุขภาพรายวัน</Link>
          <p className="eyebrow">MODEL SANDBOX</p>
          <h1>ทดสอบการทำนายสุขภาพรายวัน</h1>
          <p className="clients-intro">ป้อนข้อมูลจำลองเพื่อดู thirst score, dryness score และคำแนะนำ โดยข้อมูลจะไม่ถูกบันทึกเป็นรายการรายวัน</p>
          <PredictionTestForm initialDate={initialDate} />
        </section>
      </main>
    </div>
  );
}
