"use client";

import Link from "next/link";
import type { DailyHealthHistoryItem, HealthSignal } from "@/lib/daily-health-types";
import HealthInlineDetails from "./health-inline-details";

type Props = {
  latest?: DailyHealthHistoryItem;
  loading: boolean;
  failed: boolean;
  requiresLogin: boolean;
  onRetry: () => void;
  language: string;
  dateLabel: (date: string) => string;
};

function hasForecast(signal: HealthSignal) {
  return signal.status === "predicted" && typeof signal.value_0_10 === "number"
    && Number.isFinite(signal.value_0_10) && signal.value_0_10 >= 0 && signal.value_0_10 <= 10;
}

export default function DashboardInsights({ latest, loading, failed, requiresLogin, onRetry, language, dateLabel }: Props) {
  const t = (th: string, en: string) => language === "th" ? th : en;
  const ready = !loading && !failed && !requiresLogin && latest;
  const interpretation = ready ? latest.interpretation : null;
  const summary = interpretation?.daily_health_summary;
  const signals = interpretation ? [summary!, interpretation.skin_care_attention_level,
    interpretation.next_day_predictions.low_energy_signal,
    interpretation.next_day_predictions.thirst_attention] : [];
  const unavailableCount = signals.filter(signal => signal.level === null && !hasForecast(signal)).length;
  // Show saved messages only; deduplicate identical guidance without rewriting it.
  const recommendations = interpretation ? [...new Set([
    ...(summary?.recommendations ?? []), ...(interpretation.skin_care_attention_level.recommendations ?? []),
  ])].slice(0, 2) : [];
  const forecasts = interpretation ? [
    { label: t("พลังงานวันถัดไป", "Next-day energy"), signal: interpretation.next_day_predictions.low_energy_signal },
    { label: t("กระหายน้ำวันถัดไป", "Next-day thirst"), signal: interpretation.next_day_predictions.thirst_attention },
  ].filter(({ signal }) => hasForecast(signal)) : [];

  return <section className="home-insights-card" aria-label={t("สัญญาณและคำแนะนำจากข้อมูลล่าสุด", "Signals and guidance from your latest record")}>
    <header className="home-card-heading">
      <h2>{t("สิ่งที่ควรใส่ใจ", "Personal insights")}</h2>
      {ready ? <span className="home-period">{t("จากบันทึก", "From your record on")} <time dateTime={latest.local_date}>{dateLabel(latest.local_date)}</time></span> : null}
    </header>
    {!ready ? <div className="home-insights-state" role="status">
      {requiresLogin ? <><p>{t("เข้าสู่ระบบเพื่อดูสรุปจากบันทึกของคุณ", "Sign in to see insights from your records.")}</p><Link className="text-button" href="/login">{t("เข้าสู่ระบบ", "Sign in")}</Link></>
        : loading ? <p>{t("กำลังโหลดสรุปของคุณ…", "Loading your insights…")}</p>
        : failed ? <><p>{t("ยังโหลดสรุปจากบันทึกไม่ได้", "Unable to load your insights.")}</p><button type="button" className="secondary-button" onClick={onRetry}>{t("ลองอีกครั้ง", "Retry")}</button></>
        : <><p>{t("เริ่มบันทึกสุขภาพเพื่อดูสิ่งที่ควรใส่ใจเฉพาะคุณ", "Record your daily health to start your personal insights.")}</p><Link className="text-button" href="/clients">{t("บันทึกวันนี้", "Log today")}</Link></>}
    </div> : <div className="home-insights-content">
      <div className={`home-insights-lead${summary?.level ? ` health-signal-${summary.level}` : ""}`}>
        <h3>{t("จากบันทึกล่าสุด", "From your latest record")}</h3>
        {summary?.level ? <span className={`health-signal-level health-signal-level-${summary.level}`}>{t("ภาพรวม", "Overall")}: {summary.level === "low" ? t("ต่ำ", "Low") : summary.level === "moderate" ? t("ปานกลาง", "Moderate") : t("สูง", "High")}</span> : null}
        <p lang={summary?.headline ? "th" : undefined}>{summary?.headline ?? t("ดูผลที่มีและสถานะการประเมินด้านล่าง", "Review available results and assessment status below.")}</p>
      </div>
      {recommendations.length ? <div className="home-insights-actions"><h3>{t("สิ่งที่ควรใส่ใจ", "Things to consider")}</h3><ul>{recommendations.map(message => <li key={message} lang="th">{message}</li>)}</ul>{language === "en" ? <small>Saved guidance is shown in its original Thai.</small> : null}</div> : null}
      {forecasts.length ? <div className="home-insights-forecasts">{forecasts.map(({ label, signal }) => <div key={label}><h3>{label}</h3><p><strong>{signal.value_0_10} / 10</strong> · {t("ค่าประมาณทดลอง", "Experimental estimate")}</p>{signal.target_date ? <p>{t("สำหรับ", "For")} <time dateTime={signal.target_date}>{dateLabel(signal.target_date)}</time></p> : null}<small>{signal.target === "perceived_energy" ? t("ค่าสูงหมายถึงรู้สึกมีพลังงานมากขึ้น", "Higher means more perceived energy.") : t("ความกระหายที่รู้สึก ไม่ใช่สูตรน้ำดื่มตามน้ำหนัก", "Perceived thirst, not the weight-based water formula.")}</small></div>)}</div> : null}
      {unavailableCount ? <p className="home-insights-availability">{t(`ยังประเมินไม่ได้ ${unavailableCount} สัญญาณ — ดูเหตุผลในรายละเอียด`, `${unavailableCount} signals not assessed — see reasons in details.`)}</p> : null}
      <HealthInlineDetails interpretation={latest.interpretation} language={language === "th" ? "th" : "en"} date={dateLabel(latest.local_date)} className="home-insights-details" />
      <footer className="home-insights-footer"><p>{t("สัญญาณจากบันทึกสุขภาพ ไม่ใช่การวินิจฉัย", "Signals from your health records—not a diagnosis.")}</p><Link className="text-button" href="/trend">{t("ดูประวัติและแนวโน้ม", "View history & trends")}</Link></footer>
    </div>}
  </section>;
}
