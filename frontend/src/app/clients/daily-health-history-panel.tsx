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
const DAILY_HEALTH_DATA_UPDATED_EVENT = "daily-health-data-updated";

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

function todayInBangkok(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Bangkok",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function shiftDate(value: string, days: number): string {
  const [year, month, day] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + days));
  return [shifted.getUTCFullYear(), String(shifted.getUTCMonth() + 1).padStart(2, "0"),
    String(shifted.getUTCDate()).padStart(2, "0")].join("-");
}

function average(values: Array<number | null | undefined>): number | null {
  const validValues = values.filter((value): value is number =>
    typeof value === "number" && Number.isFinite(value));
  if (validValues.length === 0) return null;
  return validValues.reduce((sum, value) => sum + value, 0) / validValues.length;
}

function averageValue(value: number | null, fractionDigits = 1): string {
  return value === null ? "—" : value.toLocaleString("th-TH", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function WeeklySummary({ items }: { items: DailyHealthHistoryItem[] }) {
  const totalDays = 7;
  const metrics = [
    {
      label: "นอนเฉลี่ย",
      value: average(items.map((item) => item.input.sleep_duration_total_minutes)),
      format: (value: number | null) => value === null ? "—" : durationLabel(Math.round(value)),
      unit: "",
      count: items.filter((item) => Number.isFinite(item.input.sleep_duration_total_minutes)).length,
    },
    {
      label: "คะแนนการนอนเฉลี่ย",
      value: average(items.map((item) => item.calculated.sleep_score_0_100)),
      format: (value: number | null) => averageValue(value),
      unit: "/ 100",
      count: items.filter((item) => Number.isFinite(item.calculated.sleep_score_0_100)).length,
    },
    {
      label: "น้ำดื่มเฉลี่ย",
      value: average(items.map((item) => item.input.water_intake_ml)),
      format: (value: number | null) => averageValue(value, 0),
      unit: "มล./วัน",
      count: items.filter((item) => Number.isFinite(item.input.water_intake_ml)).length,
    },
    {
      label: "Thirst score เฉลี่ยตามสูตรน้ำหนัก",
      value: average(items.filter((item) => item.predictions.thirst_score_0_10.status === "calculated")
        .map((item) => item.predictions.thirst_score_0_10.value)),
      format: (value: number | null) => averageValue(value),
      unit: "/ 10",
      count: items.filter((item) => item.predictions.thirst_score_0_10.status === "calculated"
        && item.predictions.thirst_score_0_10.value !== null).length,
    },
    {
      label: "Dryness score เฉลี่ยจากโมเดล",
      value: average(items.map((item) => item.predictions.skin_dryness_score_0_10.value)),
      format: (value: number | null) => averageValue(value),
      unit: "/ 10",
      count: items.filter((item) => item.predictions.skin_dryness_score_0_10.value !== null).length,
    },
  ];

  return (
    <section className="daily-weekly-summary" aria-label="ค่าเฉลี่ยสุขภาพ 7 วันล่าสุด">
      <div className="daily-weekly-summary-heading">
        <div>
          <p className="eyebrow">LAST 7 DAYS</p>
          <h3>ค่าเฉลี่ยและข้อมูลของคุณใน 7 วันล่าสุด</h3>
          <p className="daily-weekly-summary-note">
            thirst เฉลี่ยเฉพาะคะแนนสูตรน้ำหนักรุ่นปัจจุบัน; dryness เฉลี่ยผลคาดการณ์ที่บันทึกไว้ วันที่ไม่มีค่าจะไม่นำมาคำนวณ
          </p>
        </div>
        <span>บันทึกแล้ว {items.length}/{totalDays} วัน</span>
      </div>
      <div className="daily-weekly-summary-grid">
        {metrics.map((metric) => (
          <article className="daily-weekly-summary-card" key={metric.label}>
            <p>{metric.label}</p>
            <strong>{metric.format(metric.value)} <span>{metric.unit}</span></strong>
            <small>มีข้อมูล {metric.count}/{totalDays} วัน</small>
          </article>
        ))}
      </div>
    </section>
  );
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
  const limit = view === "overview" ? 7 : 30;
  const title = view === "overview" ? "สรุปสุขภาพและความเสี่ยงรายสัปดาห์" : "แนวโน้มความเสี่ยงรายวัน";

  useEffect(() => {
    const controller = new AbortController();
    const refreshHistory = () => {
      setHistory(null);
      setFailed(false);
      setRetryCount((count) => count + 1);
    };
    window.addEventListener(DAILY_HEALTH_DATA_UPDATED_EVENT, refreshHistory);

    const today = todayInBangkok();
    const dateRange = view === "overview"
      ? `&from_date=${shiftDate(today, -6)}&to_date=${today}`
      : "";
    void fetch(`/api/daily-health/entries?limit=${limit}${dateRange}`, {
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

    return () => {
      controller.abort();
      window.removeEventListener(DAILY_HEALTH_DATA_UPDATED_EVENT, refreshHistory);
    };
  }, [limit, retryCount, view]);

  const items = history?.items ?? [];
  const visibleItems = view === "overview" ? items.slice(0, 7) : items;

  return (
    <section className={`daily-history-panel daily-history-${view}`} aria-label={title}>
      <header className="daily-history-panel-heading">
        <div>
          <p className="eyebrow">{view === "overview" ? "WEEKLY HEALTH OVERVIEW" : "HEALTH RISK HISTORY"}</p>
          <h2>{title}</h2>
          <p>
            {view === "overview"
              ? "สรุปค่าเฉลี่ยจากวันที่มีบันทึกจริงใน 7 วันปฏิทินล่าสุด พร้อมข้อมูลรายวันของคุณ"
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
          <h3>{view === "overview" ? "ยังไม่มีข้อมูลใน 7 วันล่าสุด" : "ยังไม่มีข้อมูลรายวันที่บันทึกไว้"}</h3>
          <p>
            {view === "overview"
              ? "บันทึกสุขภาพรายวันเพื่อเริ่มดูค่าเฉลี่ยและแนวโน้มเฉพาะคุณ"
              : "บันทึกข้อมูลสุขภาพรายวันก่อน แล้วผลความเสี่ยงเฉพาะคุณจะแสดงที่นี่"}
          </p>
          <Link className="primary-button" href="/clients">ไปบันทึกสุขภาพรายวัน</Link>
        </div>
      ) : (
        <>
          {view === "overview" ? <WeeklySummary items={visibleItems} /> : null}
          <div className="daily-history-list">
            {visibleItems.map((item) => <DailyHistoryEntry key={item.local_date} item={item} />)}
          </div>
        </>
      )}
    </section>
  );
}
