import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { todayInBangkok } from "@/lib/daily-health-prediction";
import PredictionTestForm from "./prediction-test-form";
import { AppNavigation } from "@/components/app-navigation";
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
    <>
      <AppNavigation active="clients" showThemeToggle />
      <div className="simple-page clients-page clients-test-page">
      <main className="page-frame">
        <section className="page-content clients-content">
          <Link className="prediction-test-back-link" href="/clients">← กลับไปสุขภาพรายวัน</Link>
          <p className="eyebrow">MODEL SANDBOX</p>
          <h1>ทดสอบการทำนายสุขภาพรายวัน</h1>
          <p className="clients-intro">ป้อนข้อมูลจำลองเพื่อดู thirst score, dryness score และคำแนะนำ โดยข้อมูลจะไม่ถูกบันทึกเป็นรายการรายวัน</p>
          <PredictionTestForm initialDate={initialDate} />
        </section>
      </main>
    </div>
    </>
  );
}
