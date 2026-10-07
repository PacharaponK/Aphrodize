"use client";

import { ChevronDown } from "lucide-react";
import type { DailyHealthInterpretation } from "@/lib/daily-health-types";
import { levelLabel, riskSignals, unavailableMessage, validForecast } from "./daily-health-risk-results";
import "./health-inline-details.css";

const unique = (values: string[]) => [...new Set(values.filter(Boolean))];

export default function HealthInlineDetails({ interpretation, language, date, className = "" }: {
  interpretation: DailyHealthInterpretation;
  language: "th" | "en";
  date: string;
  className?: string;
}) {
  const t = (th: string, en: string) => language === "th" ? th : en;
  const signals = riskSignals(interpretation, language);
  const reasons = unique(signals.flatMap(({ signal }) => [signal.headline ?? "", ...(signal.possible_signals ?? [])]));
  const guidance = unique(signals.flatMap(({ signal }) => signal.recommendations ?? []));
  const forecasts = signals.slice(2);
  const unavailable = forecasts.filter(({ signal }) => !validForecast(signal));
  const assessed = signals.slice(0, 2);

  return <details className={`health-inline-details ${className}`}>
    <summary>
      <span className="inline-details-closed">{t("เหตุผลและคำแนะนำ", "Reasons & guidance")}</span>
      <span className="inline-details-open">{t("ซ่อนรายละเอียด", "Hide details")}</span>
      <span className="sr-only"> {date}</span>
      <ChevronDown size={18} aria-hidden="true" />
    </summary>
    <div className="health-inline-body">
      <section>
        <h4>{t("จากบันทึกวันนั้น", "What your record shows")}</h4>
        <dl className="inline-assessments">{assessed.map(({ label, signal }) => <div key={label}>
          <dt>{label}</dt><dd>{levelLabel(signal, language)}</dd>
          {signal.level === null ? <dd className="inline-status-note">{unavailableMessage(signal, language)}</dd> : null}
        </div>)}</dl>
        {reasons.length ? <ul className="inline-saved-copy">{reasons.map(reason => <li key={reason} lang="th">{reason}</li>)}</ul> : null}
      </section>
      {guidance.length || interpretation.profile_guidance.length ? <section>
        <h4>{t("คำแนะนำ", "Guidance")}</h4>
        <ul className="inline-saved-copy">{guidance.map(message => <li key={message} lang="th">{message}</li>)}
          {interpretation.profile_guidance.filter(({ message, reference_url }) => !guidance.includes(message) || reference_url).map(({ topic, message, reference_url, reference_label }) => <li key={topic} lang="th">
            {guidance.includes(message) ? null : message}
            {reference_url ? <> <a href={reference_url} target="_blank" rel="noreferrer">{reference_label ?? t("แหล่งข้อมูล", "Source")}</a></> : null}
          </li>)}
        </ul>
        {language === "en" ? <p className="inline-status-note">Saved guidance is shown in its original Thai.</p> : null}
      </section> : null}
      {forecasts.length ? <section className="inline-outlook-section">
        <h4>{t("การพยากรณ์วันถัดไป", "Next-day outlook")}</h4>
        <dl className="inline-forecasts">{forecasts.filter(({ signal }) => validForecast(signal)).map(({ label, signal }) => <div key={label}>
          <dt>{label}</dt><dd><strong>{signal.value_0_10} / 10</strong> · {t("ค่าประมาณทดลอง", "Experimental estimate")}</dd>
          <dd>{t("สำหรับ", "For")} <time dateTime={signal.target_date}>{signal.target_date ?? t("ไม่ระบุวันที่", "Date unavailable")}</time></dd>
          <dd className="inline-status-note">{signal.target === "perceived_energy"
            ? t("ค่าสูงหมายถึงรู้สึกมีพลังงานมากขึ้น", "Higher means more perceived energy.")
            : t("ความกระหายที่รู้สึก ไม่ใช่สูตรน้ำดื่มตามน้ำหนัก", "Perceived thirst, not the weight-based water formula.")}</dd>
        </div>)}</dl>
        {unavailable.length ? <div className="inline-unavailable"><dl>{unavailable.map(({ label, signal }) => <div key={label}>
          <dt>{label}</dt><dd>{levelLabel(signal, language)}</dd>
        </div>)}</dl>
          {unique(unavailable.map(({ signal }) => unavailableMessage(signal, language))).map(message => <p className="inline-status-note" key={message}>{message}</p>)}
          {unavailable.some(({ signal }) => ["insufficient_data", "insufficient_history"].includes(signal.status)) ? <a className="text-button" href="/clients#daily-outcome-title">{t("บันทึกผลที่สังเกตจริง", "Record observed outcomes")}</a> : null}
        </div> : null}
      </section> : null}
      {signals.some(({ signal }) => signal.model_id || signal.method || signal.drivers?.length || signal.reason_codes?.length) ? <details className="inline-provenance">
        <summary>{t("วิธีประเมินและที่มาของผล", "Assessment method & provenance")}</summary>
        <dl>{signals.filter(({ signal }) => signal.model_id || signal.method || signal.drivers?.length || signal.reason_codes?.length).map(({ label, signal }) => <div key={label}>
          <dt>{label}</dt><dd>{signal.model_id}</dd>{signal.method ? <dd>{signal.method}</dd> : null}
          {unique([...(signal.drivers ?? []), ...(signal.reason_codes ?? [])]).map(code => <dd key={code}>{code}</dd>)}
        </div>)}</dl>
      </details> : null}
      <p className="inline-status-note">{t("สัญญาณจากบันทึกสุขภาพ ไม่ใช่การวินิจฉัย", "Signals from your health records—not a diagnosis.")}</p>
    </div>
  </details>;
}
