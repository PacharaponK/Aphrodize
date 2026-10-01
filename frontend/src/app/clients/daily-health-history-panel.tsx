"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, Check, Droplets, Moon, Plus, ScanFace, TrendingUp } from "lucide-react";
import type {
  DailyHealthHistoryItem,
  DailyHealthHistoryResponse,
  HealthSignal,
} from "@/lib/daily-health-types";
import DailyHealthRiskResults from "./daily-health-risk-results";

type HistoryView = "overview" | "trend" | "dashboard";
const DAILY_HEALTH_DATA_UPDATED_EVENT = "daily-health-data-updated";

function formatDate(value: string, locale = "th-TH"): string {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, {
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
  return ["น้อยกว่า 1 ชม.", "1–น้อยกว่า 3 ชม.", "3–น้อยกว่า 4 ชม.", "4 ชม.ขึ้นไป"][choice - 1]
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

export function DashboardHistory({ items, loading, failed, requiresLogin, onRetry }: {
  items: DailyHealthHistoryItem[];
  loading: boolean;
  failed: boolean;
  requiresLogin: boolean;
  onRetry: () => void;
}) {
  const [language, setLanguage] = useState("en");
  useEffect(() => {
    const syncLanguage = () => setLanguage(localStorage.getItem("aphrodize-language") === "th" ? "th" : "en");
    syncLanguage();
    window.addEventListener("aphrodize-language-change", syncLanguage);
    return () => window.removeEventListener("aphrodize-language-change", syncLanguage);
  }, []);
  const t = (thai: string, english: string) => language === "en" ? english : thai;
  const dateLabel = (date: string) => formatDate(date, language === "en" ? "en-US" : "th-TH");
  const today = todayInBangkok();
  const dates = Array.from({ length: 7 }, (_, index) => shiftDate(today, index - 6));
  const week = dates.map((date) => items.find((item) => item.local_date === date));
  const latest = [...items].sort((a, b) => b.local_date.localeCompare(a.local_date))[0];
  const metrics = [
    { label: t("การนอน", "Sleep duration score"), Icon: Moon, unit: "/ 100", maximum: 100,
      values: week.map((item) => item?.calculated.sleep_score_0_100),
      note: t("คะแนนระยะเวลานอนตามสูตร ไม่ใช่คุณภาพการนอน", "Duration-based formula, not sleep quality") },
    { label: t("น้ำดื่ม", "Water intake"), Icon: Droplets, unit: t("มล./วัน", "ml/day"), maximum: null,
      values: week.map((item) => item?.input.water_intake_ml),
      note: t("ปริมาณน้ำดื่มที่คุณบันทึก", "The drinking water you recorded") },
    { label: "Thirst score", Icon: Droplets, unit: "/ 10", maximum: 10,
      values: week.map((item) => item?.predictions.thirst_score_0_10.status === "calculated"
        ? item.predictions.thirst_score_0_10.value : null),
      note: t("ตามสูตรน้ำหนัก · ค่าสูงหมายถึงน้ำดื่มต่ำกว่าเกณฑ์มากขึ้น", "Weight-based formula; higher means a larger recorded shortfall") },
    { label: "Dryness score", Icon: ScanFace, unit: "/ 10", maximum: 10,
      values: week.map((item) => item?.predictions.skin_dryness_score_0_10.status === "predicted"
        ? item.predictions.skin_dryness_score_0_10.value : null),
      note: t("ผลคาดการณ์ที่บันทึก · ค่าสูงหมายถึงสัญญาณผิวแห้งมากขึ้น", "Stored forecasts; higher means a stronger dryness signal") },
  ];
  const unavailable = loading || failed || requiresLogin;

  return (
    <div className="home-health-content" lang={language}>
      <section className="home-wellness-card" aria-label={t("ข้อมูลใน 7 วันล่าสุด", "Your last 7 days")}>
        <header className="home-card-heading"><h2>{t("7 วันของคุณ", "Your last 7 days")}</h2><span className="home-period">{dateLabel(dates[0])} - {dateLabel(today)}</span></header>
        <p>{t("มองเห็นความสม่ำเสมอจากวันที่คุณบันทึกจริง", "See your consistency through actual daily records")}</p>
        <ol className="home-week-grid" aria-label={t("วันที่มีบันทึกสุขภาพ", "Days with health records")}>
          {dates.map((date, index) => <li key={date}>
            <span className={`home-day${!unavailable && week[index] ? " is-recorded" : ""}`} aria-label={`${dateLabel(date)}: ${unavailable ? t("ยังไม่พร้อมแสดงข้อมูล", "Unavailable") : week[index] ? t("มีบันทึก", "Recorded") : t("ไม่มีบันทึก", "No record")}`}>
              {!unavailable && week[index] ? <Check size={20} aria-hidden="true" /> : <span aria-hidden="true">-</span>}
            </span><time dateTime={date}>{Number(date.slice(-2))}</time>
          </li>)}
        </ol>
        <div className="home-week-status" role="status">
          {requiresLogin ? <><strong>{t("เริ่มต้นภาพรวมเฉพาะคุณ", "Start your personal overview")}</strong><p>{t("เข้าสู่ระบบเพื่อดูบันทึกและคะแนนของคุณ", "Sign in to see your records and scores")}</p><Link href="/login" className="text-button">{t("เข้าสู่ระบบ", "Sign in")} <ArrowUpRight size={16} aria-hidden="true" /></Link></>
            : loading ? <p>{t("กำลังโหลดข้อมูลของคุณ…", "Loading your data…")}</p>
            : failed ? <><strong>{t("ยังโหลดข้อมูลไม่ได้", "Unable to load your records")}</strong><button type="button" className="secondary-button" onClick={onRetry}>{t("ลองอีกครั้ง", "Retry")}</button></>
            : <><strong>{week.filter(Boolean).length}<span>{t(" / 7 วันมีบันทึก", " / 7 days recorded")}</span></strong><p>{items.length ? t("วันที่ไม่มีข้อมูลจะไม่นำมาคำนวณค่าเฉลี่ย", "Missing days are excluded from averages") : t("บันทึกสุขภาพรายวันเพื่อเริ่มดูข้อมูลของคุณ", "Record your daily health to start your overview")}</p></>}
        </div>
      </section>
      <div className="home-quick-actions">
        <Link href="/clients" className="home-action-card"><Plus className="home-action-icon" aria-hidden="true" /><h2>{t("บันทึกวันนี้", "Log today")}</h2><p>{t("เวลานอน น้ำดื่ม และกลางแจ้ง", "Sleep, water and time outdoors")}</p><ArrowUpRight className="home-action-arrow" aria-hidden="true" /></Link>
        <Link href="/trend" className="home-action-card"><TrendingUp className="home-action-icon" aria-hidden="true" /><h2>{t("ประวัติและแนวโน้ม", "History & trends")}</h2><p>{t("ย้อนดูข้อมูลและความเสี่ยงรายวัน", "Review your records and daily signals")}</p><ArrowUpRight className="home-action-arrow" aria-hidden="true" /></Link>
      </div>
      <section className="home-metric-section" aria-label={t("ค่าเฉลี่ยและข้อมูลรายสัปดาห์", "Weekly averages and records")}>
        <header className="home-card-heading"><h2>{t("ภาพรวมรายสัปดาห์", "Weekly overview")}</h2><span className="home-period">{t("ค่าเฉลี่ยจากข้อมูลที่มีใน 7 วัน", "Averages from available records in the last 7 days")}</span></header>
        <div className="home-metric-grid">
          {metrics.map(({ label, Icon, unit, maximum, values, note }) => {
            const mean = unavailable ? null : average(values);
            const count = unavailable ? 0 : values.filter((value) => typeof value === "number" && Number.isFinite(value)).length;
            const scale = maximum ?? Math.max(1, ...values.map((value) => value ?? 0));
            return <article className="home-metric-card" key={label}>
              <Icon className="home-metric-icon" size={22} aria-hidden="true" /><h3>{label}</h3>
              <p className="home-metric-value">{mean === null ? "-" : averageValue(mean, maximum === null ? 0 : 1)} <span>{unit}</span></p>
              <p className="home-metric-note">{note}</p>
              {mean === null ? <div className="home-chart-empty">{loading && !requiresLogin ? t("กำลังโหลด…", "Loading…") : t("ยังไม่มีข้อมูล", "No data yet")}</div> : <>
                <svg viewBox="0 0 240 64" className="home-metric-chart" role="img" aria-label={`${label}: ${values.map((value, index) => `${dateLabel(dates[index])} ${typeof value === "number" && Number.isFinite(value) ? value : t("ไม่มีค่า", "no value")}`).join("; ")}`}>
                  {values.map((value, index) => typeof value === "number" && Number.isFinite(value) ? <rect key={index} x={index * 34 + 5} y={60 - Math.max(0, Math.min(56, value / scale * 56))} width="22" height={Math.max(0, Math.min(56, value / scale * 56))} rx="3"><title>{`${dateLabel(dates[index])}: ${value} ${unit}`}</title></rect> : null)}
                </svg>
                <div className="home-chart-days" aria-hidden="true">{dates.map((date) => <span key={date}>{Number(date.slice(-2))}</span>)}</div>
                <p className="home-chart-caption">{count}/7 {t("วันมีค่า", "days with data")}</p>
                <details className="home-chart-data"><summary>{t("ดูค่ารายวัน", "View daily values")}</summary><ul>{dates.map((date, index) => <li key={date}><time dateTime={date}>{dateLabel(date)}</time><span>{typeof values[index] === "number" && Number.isFinite(values[index]) ? values[index] : "-"} {unit}</span></li>)}</ul></details>
              </>}
            </article>;
          })}
        </div>
      </section>
      <section className="home-insights-card" aria-label={t("สัญญาณและคำแนะนำจากข้อมูลล่าสุด", "Signals and guidance from your latest record")}>
        <header className="home-card-heading"><h2>{t("สิ่งที่ควรใส่ใจ", "Personal insights")}</h2>{latest && !unavailable ? <span className="home-period">{t("จากบันทึก", "From your record on")} {dateLabel(latest.local_date)}</span> : null}</header>
        {unavailable || !latest ? <p>{t("เมื่อมีข้อมูล ระบบจะแสดงสัญญาณและคำแนะนำเฉพาะคุณที่นี่", "Your personal signals and guidance will appear here when records are available")}</p> : <div lang="th">{language === "en" ? <p lang="en">Recorded guidance is currently available in Thai.</p> : null}<DailyHealthRiskResults interpretation={latest.interpretation} /></div>}
      </section>
      {!unavailable && items.length > 0 ? <details className="home-history-details"><summary>{t("ข้อมูลรายวันที่ใช้ในภาพรวม", "Recorded daily details (Thai)")} ({items.length} {t("วัน", "days")})</summary><div className="daily-history-list" lang="th">{[...items].sort((a, b) => b.local_date.localeCompare(a.local_date)).map((item) => <DailyHistoryEntry key={item.local_date} item={item} />)}</div></details> : null}
    </div>
  );
}

export default function DailyHealthHistoryPanel({ view }: { view: HistoryView }) {
  const [history, setHistory] = useState<DailyHealthHistoryResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const limit = view === "trend" ? 30 : 7;
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
    const dateRange = view !== "trend"
      ? `&from_date=${shiftDate(today, -6)}&to_date=${today}`
      : "";
    void fetch(`/api/daily-health/entries?limit=${limit}${dateRange}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (view === "dashboard" && response.status === 401) {
          setRequiresLogin(true);
          setHistory({ items: [] });
          return { items: [] };
        }
        if (!response.ok) throw new Error("history_unavailable");
        setRequiresLogin(false);
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

  if (view === "dashboard") return <DashboardHistory items={items} loading={history === null && !failed} failed={failed} requiresLogin={requiresLogin} onRetry={() => { setFailed(false); setHistory(null); setRetryCount((count) => count + 1); }} />;

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
