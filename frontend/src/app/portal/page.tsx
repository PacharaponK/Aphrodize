"use client";

import Link from "next/link";
import { ArrowRight, ExternalLink } from "lucide-react";
import { LanguageToggle, useLanguage } from "@/components/language-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import "./portal.css";

const applications = [
  { href: "/#dashboard", name: ["ภาพรวม", "Overview"], detail: ["รวมข้อมูลผิวและสุขภาพรายวัน", "Your skin and daily health at a glance"] },
  { href: "/capture", name: ["วิเคราะห์ภาพ", "Analyze image"], detail: ["ส่งภาพเพื่อตรวจคุณภาพและวิเคราะห์ผิว", "Upload a photo for quality checks and skin analysis"] },
  { href: "/clients", name: ["สุขภาพรายวัน", "Daily health"], detail: ["บันทึกการนอน การดื่มน้ำ และกิจวัตร", "Record sleep, water intake and daily habits"] },
  { href: "/uv-map", name: ["แผนที่ UV", "UV map"], detail: ["ดูค่าประมาณ UV รายจังหวัดในประเทศไทย", "Explore estimated UV across Thailand"] },
];

const services = [
  { href: "http://localhost:8000/docs", name: "FastAPI Docs", detail: ["เอกสาร API และทดลองเรียก endpoint", "Read API documentation and try endpoints"] },
  { href: "http://localhost:8080", name: "Label Studio", detail: ["จัดการงาน annotation และตรวจทานภาพ", "Annotate data and review images"] },
  { href: "http://localhost:5000", name: "MLflow", detail: ["ดู training runs, metrics และ model artifacts", "Explore training runs, metrics and model artifacts"] },
  { href: "http://localhost:9001", name: "MinIO Console", detail: ["จัดการ buckets และไฟล์ของระบบ", "Manage system buckets and stored files"] },
];

const monitoring = [
  { href: "http://localhost:3001/d/aphrodize-system", name: "Grafana", detail: ["ดูภาพรวมระบบ งานประมวลผล และ UV พร้อมค้นหา logs ใน Explore", "Inspect system, job and UV dashboards; search logs in Explore"] },
  { href: "http://localhost:3001/alerting/notifications", name: ["ทดสอบ Discord alert", "Test Discord alerts"], detail: ["เลือก operations แล้วกด Test เพื่อทดสอบส่งข้อความเข้าห้อง Discord", "Select operations, then Test to verify delivery to your Discord channel"] },
  { href: "http://localhost:9090/targets", name: "Prometheus", detail: ["ตรวจ targets ที่เก็บ metrics และดูข้อผิดพลาดการเชื่อมต่อ", "Check metric scrape targets and connection errors"] },
];

export default function PortalPage() {
  const { language } = useLanguage();
  const locale = language === "th" ? 0 : 1;

  return (
    <main className="portal-page" data-color-system="hierarchical">
      <header className="portal-header">
        <div className="portal-controls"><LanguageToggle /><ThemeToggle /></div>
        <h1>{locale === 0 ? "ทุกเซอร์วิส ในที่เดียว" : "Every service. One place."}</h1>
        <p>{locale === 0 ? "เลือกทางเข้าใช้งาน Aphrodize และเครื่องมือของระบบ" : "Your starting point for Aphrodize and its system tools."}</p>
      </header>

      <section className="portal-applications" aria-labelledby="portal-apps-title">
        <div className="portal-section-intro">
          <h2 id="portal-apps-title">{locale === 0 ? "ใช้งาน Aphrodize" : "Use Aphrodize"}</h2>
          <p>{locale === 0 ? "เริ่มจากสิ่งที่คุณอยากทำวันนี้" : "Start with what you want to do today."}</p>
        </div>
        <div className="portal-app-links">
          {applications.map((app) => (
            <Link key={app.href} href={app.href} className="portal-app-link">
              <span><strong>{app.name[locale]}</strong><span>{app.detail[locale]}</span></span>
              <ArrowRight size={22} aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>

      <section className="portal-tools portal-monitoring" aria-labelledby="portal-monitoring-title">
        <div className="portal-section-intro">
          <h2 id="portal-monitoring-title">{locale === 0 ? "ติดตามระบบและการแจ้งเตือน" : "Monitoring and alerts"}</h2>
          <p>{locale === 0 ? "ดู metrics, logs และทดสอบการแจ้งเตือนผ่าน UI" : "Explore metrics, logs and test notification delivery."}</p>
        </div>
        <div className="portal-service-list">
          {monitoring.map((service) => (
            <a key={service.href} href={service.href} target="_blank" rel="noopener noreferrer" className="portal-service-link">
              <strong>{typeof service.name === "string" ? service.name : service.name[locale]}</strong>
              <span className="portal-service-detail">{service.detail[locale]}</span>
              <span className="portal-service-address">{service.href}</span>
              <ExternalLink size={18} aria-hidden="true" />
            </a>
          ))}
        </div>
        <p className="portal-note">{locale === 0 ? "ต้องเริ่มชุด observability ก่อน เปิดจากเครื่องที่รัน Docker หรือเชื่อม SSH tunnel ไปยัง VM การทดสอบ Discord ต้องตั้ง webhook ของห้องไว้ก่อน" : "Start the observability stack first. Open from the Docker host or through an SSH tunnel to the VM. Discord testing requires your channel webhook."}</p>
      </section>

      <section className="portal-tools" aria-labelledby="portal-tools-title">
        <div className="portal-section-intro">
          <h2 id="portal-tools-title">{locale === 0 ? "เครื่องมือของระบบ" : "System tools"}</h2>
          <p>{locale === 0 ? "Local Docker · เปิดในแท็บใหม่" : "Local Docker · Opens in a new tab"}</p>
        </div>
        <div className="portal-service-list">
          {services.map((service) => (
            <a key={service.name} href={service.href} target="_blank" rel="noopener noreferrer" className="portal-service-link">
              <strong>{service.name}</strong>
              <span className="portal-service-detail">{service.detail[locale]}</span>
              <span className="portal-service-address">{service.href}</span>
              <ExternalLink size={18} aria-hidden="true" />
            </a>
          ))}
          <Link href="/admin" className="portal-service-link portal-admin-link">
            <strong>{locale === 0 ? "จัดการผลิตภัณฑ์" : "Product catalog"}</strong>
            <span className="portal-service-detail">{locale === 0 ? "ตรวจทานและจัดการแคตตาล็อกผลิตภัณฑ์" : "Review and manage the product catalog"}</span>
            <span className="portal-service-address">/admin</span>
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        </div>
        <p className="portal-note">{locale === 0 ? "ลิงก์ localhost ใช้กับเครื่องที่รัน Docker เท่านั้น แต่ละเครื่องมือใช้บัญชีของตัวเอง และต้องเริ่มเซอร์วิสก่อนใช้งาน" : "Localhost links work on the computer running Docker. Start the services first; each tool uses its own sign-in."}</p>
      </section>
    </main>
  );
}
