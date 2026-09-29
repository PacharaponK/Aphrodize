import type { Metadata } from "next";
import Script from "next/script";
import Link from "next/link";
import { Camera, ArrowUpRight } from "lucide-react";
import { AppNavigation } from "../components/app-navigation";
import HomeMotionVideo from "../components/home-motion-video";
import { HomeScrollMotion } from "../components/home-scroll-motion";
import DailyHealthHistoryPanel from "./clients/daily-health-history-panel";
import "./clients/clients.css";
import "./clients/daily-health-history.css";
import "./home.css";

export const metadata: Metadata = { title: "Aphrodize — Skin tracking" };

export default function Page() {
  return (
    <div className="app-shell home-dashboard-shell" lang="en">
      <HomeScrollMotion />
      <AppNavigation active="dashboard" initialLanguage="en" />
      <main id="dashboard">
        <figure className="home-motion-frame" aria-hidden="true"><HomeMotionVideo /></figure>
        <header className="topbar home-topbar">
          <div>
            <h1>Your daily overview</h1>
            <p className="home-intro">Your skin, sleep and hydration in one place.</p>
          </div>
          <Link className="primary-button home-log-action" href="/clients"><span>Log today</span><ArrowUpRight size={18} aria-hidden="true" /></Link>
          <button className="avatar" aria-label="Sign in" type="button">Sign in</button>
        </header>
        <section className="home-dashboard-grid" aria-label="Skin and daily health overview">
          <article className="home-overview-card">
            <p className="home-media-label">Background video, not an analysis result</p>
            <div className="home-overview-score">
              <h2>Know your skin. Day by day.</h2>
              <p>Track your skin images alongside your sleep and hydration habits.</p>
              <Link className="primary-button" href="/capture"><Camera size={18} aria-hidden="true" /> <span>Analyze skin</span> <ArrowUpRight size={18} aria-hidden="true" /></Link>
            </div>
          </article>
          <DailyHealthHistoryPanel view="dashboard" />
        </section>
        <p className="home-safety-note">Scores and signals support personal tracking; they are not a medical diagnosis.</p>
      </main>
      <Script src="/legacy/home.js" strategy="afterInteractive" />
    </div>
  );
}



