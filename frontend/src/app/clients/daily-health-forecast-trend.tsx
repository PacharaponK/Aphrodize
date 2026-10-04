"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, RefreshCw, TrendingUp } from "lucide-react";
import type {
  DailyHealthPersonalForecast,
  PersonalForecastDay,
  PersonalForecastMetric,
} from "@/lib/daily-health-types";

type Language = "en" | "th";
type ForecastMetric = "sleep_duration_minutes" | "water_intake_ml";

function translate(language: Language, thai: string, english: string): string {
  return language === "th" ? thai : english;
}

function formatDate(value: string, language: Language, includeYear = false): string {
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return new Intl.DateTimeFormat(language === "th" ? "th-TH" : "en-US", {
    day: "numeric",
    month: "short",
    ...(includeYear ? { year: "numeric" as const } : {}),
    timeZone: "UTC",
  }).format(date);
}

function metricValue(day: PersonalForecastDay, metric: ForecastMetric): number | null {
  return day[metric];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDateString(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}

function isPersonalForecastMetric(value: unknown): value is PersonalForecastMetric {
  if (!isRecord(value)) return false;
  if (value.status === "insufficient_history") return value.value === null;
  return value.status === "predicted" && typeof value.value === "number" && Number.isFinite(value.value);
}

function isPersonalForecastDay(value: unknown): value is PersonalForecastDay {
  if (!isRecord(value) || !isDateString(value.local_date)) return false;
  const validSleep = value.sleep_duration_minutes === null
    || (Number.isInteger(value.sleep_duration_minutes)
      && Number(value.sleep_duration_minutes) >= 0
      && Number(value.sleep_duration_minutes) <= 600);
  const validWater = value.water_intake_ml === null
    || (Number.isInteger(value.water_intake_ml)
      && Number(value.water_intake_ml) >= 0
      && Number(value.water_intake_ml) <= 20_000);
  return validSleep && validWater;
}

function isPersonalForecastResponse(value: unknown): value is DailyHealthPersonalForecast {
  if (!isRecord(value) || typeof value.enabled !== "boolean") return false;
  if (!value.enabled) {
    return value.status === "consent_required" || value.status === "daily_health_consent_required";
  }
  if (value.status !== "forecasted" && value.status !== "insufficient_history") return false;
  if (!isDateString(value.prediction_target_date)
    || !isDateString(value.history_start_date)
    || !isDateString(value.history_end_date)
    || !Array.isArray(value.actual)
    || value.actual.length !== 7
    || !value.actual.every(isPersonalForecastDay)
    || !isRecord(value.predictions)
    || !isPersonalForecastMetric(value.predictions.sleep_duration_minutes)
    || !isPersonalForecastMetric(value.predictions.water_intake_ml)
    || !isRecord(value.model)) return false;
  return value.model.scope === "account_only"
    && value.model.prediction_horizon_days === 1
    && Number.isInteger(value.model.observations_used)
    && Number.isInteger(value.model.minimum_observations);
}

function displayValue(metric: ForecastMetric, value: number, language: Language): string {
  if (metric === "sleep_duration_minutes") {
    const hours = value / 60;
    return `${hours.toLocaleString(language === "th" ? "th-TH" : "en-US", {
      maximumFractionDigits: 1,
    })} ${translate(language, "ชม.", "hr")}`;
  }
  return `${value.toLocaleString(language === "th" ? "th-TH" : "en-US")} ${translate(language, "มล.", "ml")}`;
}

export function ForecastLineChart({
  metric,
  language,
  actual,
  targetDate,
  forecastValue,
}: {
  metric: ForecastMetric;
  language: Language;
  actual: PersonalForecastDay[];
  targetDate: string;
  forecastValue: number | null;
}) {
  const heading = metric === "sleep_duration_minutes"
    ? translate(language, "เวลานอน", "Sleep duration")
    : translate(language, "น้ำดื่ม", "Water intake");
  const unit = metric === "sleep_duration_minutes"
    ? translate(language, "ชั่วโมง", "hours")
    : translate(language, "มล.", "ml");
  const values = actual.map((day) => metricValue(day, metric));
  const numericValues = values.filter((value): value is number => value !== null);
  const chartValues = forecastValue === null ? numericValues : [...numericValues, forecastValue];
  const minimum = chartValues.length ? Math.min(...chartValues) : 0;
  const maximum = chartValues.length ? Math.max(...chartValues) : 1;
  const range = maximum - minimum || Math.max(1, maximum * 0.1);
  const lowerBound = Math.max(0, minimum - range * 0.18);
  const upperBound = maximum + range * 0.18;
  const x = (index: number) => 22 + index * 42;
  const y = (value: number) => 100 - ((value - lowerBound) / (upperBound - lowerBound)) * 76;
  const lastActualIndex = values.reduce<number>(
    (last, value, index) => value === null ? last : index,
    -1,
  );
  const lastActualValue = lastActualIndex >= 0 ? values[lastActualIndex] : null;
  const formattedForecast = forecastValue === null
    ? translate(language, "ยังไม่มีค่าพยากรณ์", "No forecast yet")
    : displayValue(metric, forecastValue, language);
  const dateRange = actual.length > 0
    ? `${formatDate(actual[0].local_date, language)}–${formatDate(actual[actual.length - 1].local_date, language)}`
    : translate(language, "ยังไม่มีวันที่บันทึก", "no recorded days");
  const accessibleLabel = translate(
    language,
    `${heading}: ค่าจริง ${dateRange}; ค่าประมาณวันถัดไป ${formatDate(targetDate, language, true)} ${formattedForecast}`,
    `${heading}: actual values ${dateRange}; next-day forecast ${formatDate(targetDate, language, true)} ${formattedForecast}`,
  );

  return (
    <article className="personal-forecast-metric-card">
      <header className="personal-forecast-metric-heading">
        <div>
          <p className="eyebrow">{translate(language, "ข้อมูลที่บันทึกจริง", "ACTUAL DAILY RECORDS")}</p>
          <h3>{heading}</h3>
        </div>
        <span className="personal-forecast-metric-unit">{unit}</span>
      </header>
      <figure className="personal-forecast-chart">
        <svg viewBox="0 0 332 122" role="img" aria-label={accessibleLabel}>
          <line className="personal-forecast-grid-line" x1="18" x2="324" y1="100" y2="100" />
          {values.slice(0, -1).map((value, index) => {
            const nextValue = values[index + 1];
            if (value === null || nextValue === null) return null;
            return (
              <line
                className="personal-forecast-actual-line"
                data-series="actual"
                key={`actual-${index}`}
                x1={x(index)}
                x2={x(index + 1)}
                y1={y(value)}
                y2={y(nextValue)}
              />
            );
          })}
          {forecastValue !== null && lastActualIndex >= 0 && lastActualValue !== null ? (
            <line
              className="personal-forecast-next-line"
              data-series="forecast"
              x1={x(lastActualIndex)}
              x2={x(7)}
              y1={y(lastActualValue)}
              y2={y(forecastValue)}
            />
          ) : null}
          {values.map((value, index) => value === null ? null : (
            <circle
              className="personal-forecast-actual-point"
              data-series="actual"
              key={`point-${actual[index].local_date}`}
              cx={x(index)}
              cy={y(value)}
              r="4"
            >
              <title>{`${formatDate(actual[index].local_date, language, true)}: ${displayValue(metric, value, language)}`}</title>
            </circle>
          ))}
          {forecastValue !== null ? (
            <rect
              className="personal-forecast-predicted-point"
              data-series="forecast"
              x={x(7) - 4}
              y={y(forecastValue) - 4}
              width="8"
              height="8"
              rx="2"
            >
              <title>{`${translate(language, "ค่าประมาณ", "Forecast")}, ${formatDate(targetDate, language, true)}: ${formattedForecast}`}</title>
            </rect>
          ) : null}
          <text className="personal-forecast-axis-label" x="22" y="118">
            {actual.length ? formatDate(actual[0].local_date, language) : "-"}
          </text>
          <text className="personal-forecast-axis-label" textAnchor="middle" x="148" y="118">
            {actual.length ? formatDate(actual[Math.floor((actual.length - 1) / 2)].local_date, language) : "-"}
          </text>
          <text className="personal-forecast-axis-label" textAnchor="end" x="330" y="118">
            {formatDate(targetDate, language)}
          </text>
        </svg>
        <figcaption className="personal-forecast-legend">
          <span><i className="personal-forecast-legend-actual" aria-hidden="true" />{translate(language, "ข้อมูลจริง", "Actual")}</span>
          <span><i className="personal-forecast-legend-estimate" aria-hidden="true" />{translate(language, "ประมาณวันถัดไป", "Next-day forecast")}</span>
        </figcaption>
      </figure>
      <details className="personal-forecast-values">
        <summary>{translate(language, "ดูค่ารายวัน", "View daily values")}</summary>
        <ul>
          {actual.map((day) => {
            const value = metricValue(day, metric);
            return (
              <li key={day.local_date}>
                <time dateTime={day.local_date}>{formatDate(day.local_date, language, true)}</time>
                <span>{value === null ? "—" : displayValue(metric, value, language)}</span>
              </li>
            );
          })}
          <li className="personal-forecast-value-row">
            <time dateTime={targetDate}>{formatDate(targetDate, language, true)}</time>
            <span>{formattedForecast}</span>
          </li>
        </ul>
      </details>
    </article>
  );
}

export default function DailyHealthForecastTrend() {
  const [language, setLanguage] = useState<Language>("en");
  const [forecast, setForecast] = useState<DailyHealthPersonalForecast | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [actionError, setActionError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const syncLanguage = () => {
      setLanguage(localStorage.getItem("aphrodize-language") === "th" ? "th" : "en");
    };
    const refresh = () => setRevision((current) => current + 1);
    syncLanguage();
    window.addEventListener("aphrodize-language-change", syncLanguage);
    window.addEventListener("daily-health-data-updated", refresh);

    const controller = new AbortController();
    void fetch("/api/daily-health/personal-forecast", {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.status === 401) {
          setSignedOut(true);
          setForecast(null);
          return;
        }
        if (!response.ok) throw new Error("personal_forecast_unavailable");
        const result: unknown = await response.json();
        if (!isPersonalForecastResponse(result)) {
          throw new Error("invalid_personal_forecast_response");
        }
        setSignedOut(false);
        setForecast(result as DailyHealthPersonalForecast);
        setLoadError(false);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLoadError(true);
      });

    return () => {
      controller.abort();
      window.removeEventListener("aphrodize-language-change", syncLanguage);
      window.removeEventListener("daily-health-data-updated", refresh);
    };
  }, [revision]);

  const t = (thai: string, english: string) => translate(language, thai, english);
  const updateConsent = async (method: "PUT" | "DELETE") => {
    setBusy(true);
    setActionError(false);
    try {
      const response = await fetch("/api/daily-health/personal-forecast", {
        method,
        cache: "no-store",
      });
      if (!response.ok) throw new Error("personal_forecast_consent_failed");
      if (method === "DELETE") setForecast(null);
      setRevision((current) => current + 1);
    } catch {
      setActionError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="personal-forecast-panel" aria-labelledby="personal-forecast-heading" lang={language}>
      <header className="personal-forecast-panel-heading">
        <div>
          <p className="eyebrow">{t("การคาดการณ์เฉพาะบัญชี", "ACCOUNT-ONLY FORECAST")}</p>
          <h2 id="personal-forecast-heading">{t("แนวโน้มข้อมูลของคุณ", "Your personal outlook")}</h2>
          <p>{t(
            "เปรียบเทียบบันทึกจริง 7 วันกับค่าประมาณเวลานอนและน้ำดื่มในวันถัดไป",
            "Compare seven days of real entries with next-day estimates for sleep and water.",
          )}</p>
        </div>
        <TrendingUp size={22} aria-hidden="true" />
      </header>

      {loadError ? (
        <div className="personal-forecast-state" role="alert">
          <p>{t("ยังโหลดการคาดการณ์ส่วนตัวไม่ได้", "Could not load your personal forecast.")}</p>
          <button className="secondary-button" type="button" onClick={() => setRevision((current) => current + 1)}>
            <RefreshCw size={16} aria-hidden="true" /> {t("ลองอีกครั้ง", "Retry")}
          </button>
        </div>
      ) : signedOut ? (
        <div className="personal-forecast-state" role="status">
          <p>{t("เข้าสู่ระบบเพื่อดูแนวโน้มเฉพาะบัญชีของคุณ", "Sign in to view forecasts from your own account history.")}</p>
          <Link className="secondary-button" href="/login">{t("เข้าสู่ระบบ", "Sign in")} <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </div>
      ) : forecast === null ? (
        <p className="personal-forecast-loading" role="status">{t("กำลังโหลด…", "Loading your forecast…")}</p>
      ) : forecast.status === "daily_health_consent_required" ? (
        <div className="personal-forecast-state" role="status">
          <p>{t("ต้องเปิดใช้การบันทึกสุขภาพรายวันก่อน จึงจะคำนวณแนวโน้มจากข้อมูลของคุณได้", "Enable daily health records before a personal trend can be calculated.")}</p>
          <Link className="secondary-button" href="/clients">{t("ไปบันทึกสุขภาพ", "Open daily health")} <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </div>
      ) : forecast.status === "consent_required" ? (
        <div className="personal-forecast-consent">
          <p>{t(
            "อนุญาตให้คำนวณแนวโน้มจากบันทึกจริงของบัญชีนี้เท่านั้น การเปิดใช้นี้ไม่เปลี่ยนความยินยอมฝึกโมเดลรวมที่แยกต่างหาก และปิดได้ทุกเมื่อ",
            "Allow estimates using this account’s real daily records only. This does not grant or change separate consent for shared-model training, and you can turn this feature off anytime.",
          )}</p>
          <button className="primary-button" type="button" disabled={busy} onClick={() => void updateConsent("PUT")}>
            {busy ? t("กำลังบันทึก…", "Saving…") : t("เปิดใช้การคาดการณ์ส่วนตัว", "Enable personal forecast")}
          </button>
          {actionError ? <p role="alert">{t("บันทึกการยินยอมไม่สำเร็จ ลองอีกครั้ง", "Could not save consent. Please retry.")}</p> : null}
        </div>
      ) : (
        <>
          <p className="personal-forecast-method-note">
            {t(
              `ใช้เฉพาะบันทึกจริงของบัญชีนี้ ${forecast.model?.observations_used ?? 0} วันในช่วง 7 วันล่าสุด · ต้องมีอย่างน้อย ${forecast.model?.minimum_observations ?? 3} วัน`,
              `Uses only this account’s ${forecast.model?.observations_used ?? 0} real records from the last 7 days · at least ${forecast.model?.minimum_observations ?? 3} are required`,
            )}
            <span>{t("ค่าประมาณเชิงทดลอง ไม่ใช่คำแนะนำทางการแพทย์", "Experimental estimate, not medical advice")}</span>
          </p>
          {forecast.status === "insufficient_history" ? (
            <p className="personal-forecast-insufficient" role="status">
              {t("ข้อมูลจริงยังไม่พอ ต้องมีอย่างน้อย 3 วันที่บันทึกในช่วง 7 วันล่าสุด วันที่ขาดหายจะไม่ถูกนับเป็นศูนย์", "Not enough real data yet. At least 3 recorded days in the last 7 are needed; missing days are not treated as zero.")}
            </p>
          ) : null}
          <div className="personal-forecast-chart-grid">
            <ForecastLineChart
              metric="sleep_duration_minutes"
              language={language}
              actual={forecast.actual ?? []}
              targetDate={forecast.prediction_target_date ?? ""}
              forecastValue={forecast.predictions?.sleep_duration_minutes.value ?? null}
            />
            <ForecastLineChart
              metric="water_intake_ml"
              language={language}
              actual={forecast.actual ?? []}
              targetDate={forecast.prediction_target_date ?? ""}
              forecastValue={forecast.predictions?.water_intake_ml.value ?? null}
            />
          </div>
          <footer className="personal-forecast-panel-footer">
            {actionError ? <p role="alert">{t("เปลี่ยนสถานะการยินยอมไม่สำเร็จ ลองอีกครั้ง", "Could not update forecast consent. Please retry.")}</p> : null}
            <button className="secondary-button" type="button" disabled={busy} onClick={() => void updateConsent("DELETE")}>
              {busy ? t("กำลังบันทึก…", "Saving…") : t("ปิดการคาดการณ์ส่วนตัว", "Turn off personal forecast")}
            </button>
          </footer>
        </>
      )}
    </section>
  );
}
