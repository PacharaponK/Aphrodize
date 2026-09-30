import type { Metadata } from "next";
import Link from "next/link";
import { Camera, ArrowUpRight } from "lucide-react";
import { AppNavigation } from "../components/app-navigation";
import { LocalizedText } from "../components/language-provider";
import HomeMotionVideo from "../components/home-motion-video";
import { HomeScrollMotion } from "../components/home-scroll-motion";
import DailyHealthHistoryPanel from "./clients/daily-health-history-panel";
import "./clients/clients.css";
import "./clients/daily-health-history.css";
import "./home.css";

export const metadata: Metadata = { title: "Aphrodize — Skin tracking" };

export default function Page() {
  return (
    <div className="app-shell home-dashboard-shell">
      <HomeScrollMotion />
      <AppNavigation active="dashboard" showThemeToggle showSignIn />
      <main id="dashboard">
        <figure className="home-motion-frame" aria-hidden="true"><HomeMotionVideo /></figure>
        <header className="topbar home-topbar">
          <div>
            <h1><LocalizedText th="ภาพรวมประจำวันของคุณ" en="Your daily overview" /></h1>
            <p className="home-intro"><LocalizedText th="ผิว การนอน และการดื่มน้ำในมุมมองเดียว" en="Your skin, sleep and hydration in one place." /></p>
          </div>
          <Link className="primary-button home-log-action" href="/clients"><span><LocalizedText th="บันทึกวันนี้" en="Log today" /></span><ArrowUpRight size={18} aria-hidden="true" /></Link>
        </header>
        <section className="home-dashboard-grid" aria-label="Skin and daily health overview">
          <article className="home-overview-card">
            <p className="home-media-label"><LocalizedText th="วิดีโอพื้นหลัง · ไม่ใช่ผลวิเคราะห์" en="Background video, not an analysis result" /></p>
            <div className="home-overview-score">
              <h2><LocalizedText th="รู้จักผิวของคุณในทุกวัน" en="Know your skin. Day by day." /></h2>
              <p><LocalizedText th="ติดตามภาพผิวควบคู่กับพฤติกรรมการนอนและการดื่มน้ำ" en="Track your skin images alongside your sleep and hydration habits." /></p>
              <Link className="primary-button" href="/capture"><Camera size={18} aria-hidden="true" /> <span><LocalizedText th="วิเคราะห์ผิว" en="Analyze skin" /></span> <ArrowUpRight size={18} aria-hidden="true" /></Link>
            </div>
          </article>
          <DailyHealthHistoryPanel view="dashboard" />
        </section>
        <p className="home-safety-note"><LocalizedText th="คะแนนและสัญญาณมีไว้เพื่อการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์" en="Scores and signals support personal tracking; they are not a medical diagnosis." /></p>
      </main>
    </div>
  );
}



