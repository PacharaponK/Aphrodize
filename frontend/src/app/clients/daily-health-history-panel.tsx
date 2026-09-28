"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type {
  DailyHealthHistoryItem,
  DailyHealthHistoryResponse,
  HealthSignal,
} from "@/lib/daily-health-types";
import DailyHealthRiskResults from "./daily-health-risk-results";

type HistoryView = "overview" | "trend";

function formatDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("th-TH", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Bangkok",
  }).format(new Date(Date.UTC(year, month - 1, day, 12)));
}

function durationLabel(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours} ชม. ${minutes} นาที`;
}

function outdoorLabel(choice: number): string {
  return ["น้อยกว่า 1 ชม.", "1–2 ชม.", "3–4 ชม.", "4 ชม.ขึ้นไป"][choice - 1]
    ?? "ไม่ระบุ";
}

function DailyHistoryEntry({ item }: { item: DailyHealthHistoryItem }) {
  const summary: HealthSignal = item.interpretation.daily_health_summary;

  return (
    <article className="daily-history-entry">
      <header className="daily-history-entry-heading">
        <div>
          <p className="eyebrow">บันทึกประจำวันที่</p>
          <h3><time dateTime={item.local_date}>{formatDate(item.local_date)}</time></h3>
          {item.prediction_target_date && item.prediction_target_date !== item.local_date ? (
            <p className="daily-history-target-date">
              สัญญาณคาดการณ์สำหรับ {formatDate(item.prediction_target_date)}
            </p>
          ) : null}
        </div>
        {summary.level ? (
          <span className={`health-signal-level health-signal-level-${summary.level}`}>
            ภาพรวม: {summary.level === "low" ? "ต่ำ" : summary.level === "moderate" ? "ปานกลาง" : "สูง"}
          </span>
        ) : null}
      </header>
      <div className="daily-history-input-summary" aria-label="ข้อมูลประจำวันที่บันทึก">
        <span>นอน <strong>{durationLabel(item.input.sleep_duration_total_minutes)}</strong></span>
        <span>น้ำดื่ม <strong>{item.input.water_intake_ml.toLocaleString("th-TH")} มล.</strong></span>
        <span>กลางแจ้ง <strong>{outdoorLabel(item.input.outdoor_exposure_choice)}</strong></span>
      </div>
      <DailyHealthRiskResults interpretation={item.interpretation} />
    </article>
  );
}

export default function DailyHealthHistoryPanel({ view }: { view: HistoryView }) {
  const [history, setHistory] = useState<DailyHealthHistoryResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const limit = view === "overview" ? 1 : 30;
  const title = view === "overview" ? "ความเสี่ยงจากข้อมูลสุขภาพล่าสุด" : "แนวโน้มความเสี่ยงรายวัน";

  useEffect(() => {
    const controller = new AbortController();

    void fetch(`/api/daily-health/entries?limit=${limit}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("history_unavailable");
        const result: unknown = await response.json();
        if (!result || typeof result !== "object" || !Array.isArray((result as DailyHealthHistoryResponse).items)) {
          throw new Error("invalid_history_response");
        }
        setHistory(result as DailyHealthHistoryResponse);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setFailed(true);
      });

    return () => controller.abort();
  }, [limit, retryCount]);

  const items = history?.items ?? [];
  const visibleItems = view === "overview" ? items.slice(0, 1) : items;

  return (
    <section className={`daily-history-panel daily-history-${view}`} aria-label={title}>
      <header className="daily-history-panel-heading">
        <div>
          <p className="eyebrow">{view === "overview" ? "LATEST HEALTH RISKS" : "HEALTH RISK HISTORY"}</p>
          <h2>{title}</h2>
          <p>
            {view === "overview"
              ? "สรุปสัญญาณจากรายการสุขภาพล่าสุดที่บันทึกไว้"
              : "ดูระดับความเสี่ยงและคำแนะนำแยกตามวันที่บันทึกย้อนหลังไม่เกิน 30 รายการ"}
          </p>
        </div>
      </header>

      {failed ? (
        <div className="daily-history-empty" role="status">
          <p>ยังโหลดประวัติความเสี่ยงไม่ได้</p>
          <button className="secondary-button" type="button" onClick={() => {
            setFailed(false);
            setRetryCount((count) => count + 1);
          }}>
            ลองอีกครั้ง
          </button>
        </div>
      ) : history === null ? (
        <p className="daily-history-loading" role="status">กำลังโหลดข้อมูลความเสี่ยง…</p>
      ) : visibleItems.length === 0 ? (
        <div className="daily-history-empty">
          <h3>ยังไม่มีข้อมูลรายวันที่บันทึกไว้</h3>
          <p>บันทึกข้อมูลสุขภาพรายวันก่อน แล้วผลความเสี่ยงเฉพาะคุณจะแสดงที่นี่</p>
          <Link className="primary-button" href="/clients">ไปบันทึกสุขภาพรายวัน</Link>
        </div>
      ) : (
        <div className="daily-history-list">
          {visibleItems.map((item) => <DailyHistoryEntry key={item.local_date} item={item} />)}
        </div>
      )}
    </section>
  );
}
