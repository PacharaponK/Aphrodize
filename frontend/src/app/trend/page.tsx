import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import DailyHealthHistoryPanel from "../clients/daily-health-history-panel";
import "../clients/clients.css";
import "../clients/daily-health-history.css";

export const metadata: Metadata = {
  title: "แนวโน้มความเสี่ยงสุขภาพ — Aphrodize",
  description: "ติดตามสัญญาณความเสี่ยงสุขภาพรายวันจากข้อมูลที่บันทึกไว้",
};

export default function Page() {
  return (
    <div className="simple-page clients-page trend-page">
      <main className="page-frame">
        <header className="page-header">
          <Link className="page-brand" href="/">
            <Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />
            Aphrodize
          </Link>
          <nav className="page-nav" aria-label="เมนูหลัก">
            <Link href="/">ภาพรวม</Link>
            <Link href="/capture">วิเคราะห์ภาพ</Link>
            <Link className="active" href="/trend" aria-current="page">แนวโน้ม</Link>
            <Link href="/clients">สุขภาพรายวัน</Link>
            <Link href="/profile">Skin profile</Link>
          </nav>
        </header>

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
  );
}
