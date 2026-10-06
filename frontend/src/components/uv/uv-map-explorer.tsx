"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { useLanguage } from "../language-provider";
import { ThailandUvMap, UV_LEVELS, provinceOptions, type UvProvince } from "./thailand-uv-map";

type Day = "today" | "tomorrow";
type Source = "api" | "model";
type MapResult = { date: string; timezone: string; source: Source; provinces: UvProvince[] };

function timeLabel(value: string, language: "th" | "en") {
  if (!Number.isFinite(new Date(value).getTime())) return language === "en" ? "Update time unavailable" : "เวลาอัปเดตไม่พร้อม";
  return new Intl.DateTimeFormat(language === "en" ? "en-GB" : "th-TH", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" }).format(new Date(value));
}

export function UvMapHeader() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  return <header className="uv-map-header">
    <Link href="/">{t("กลับไปหน้าภาพรวม", "Back to overview")}</Link>
    <h1>{t("แผนที่ UV ประเทศไทย", "Thailand UV map")}</h1>
    <p>{t("วางแผนกลางแจ้งด้วยค่า UV ท้องฟ้าโปร่ง เลือกจังหวัดเพื่อดูรายละเอียดของวันนี้หรือพรุ่งนี้", "Explore clear-sky UV by province for today or tomorrow to plan your time outdoors.")}</p>
  </header>;
}

export function UvMapExplorer() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const locale = language === "en" ? "en-GB" : "th-TH";
  const selectId = useId();
  const [day, setDay] = useState<Day>("today");
  const [source, setSource] = useState<Source>("api");
  const [selected, setSelected] = useState("bangkok");
  const [result, setResult] = useState<MapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/uv/map?day=${day}&source=${source}`, { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error("load_failed");
        if (payload.source !== source || !Array.isArray(payload.provinces)) throw new Error("source_mismatch");
        return payload as MapResult;
      })
      .then((payload) => { if (!controller.signal.aborted) setResult(payload); })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(cause instanceof Error && cause.message === "source_mismatch" ? "source_mismatch" : "load_failed");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [day, source, attempt]);
  function refresh(nextDay = day, nextSource = source) {
    setLoading(true); setError(""); setResult(null);
    setDay(nextDay); setSource(nextSource); setAttempt((value) => value + 1);
    if (nextSource === "model" && !modelIds.includes(selected)) setSelected("bangkok");
  }
  const modelOptions = provinceOptions.filter((p) => p.model_city !== null);
  const modelIds = modelOptions.map((p) => p.id);
  const options = source === "model" ? modelOptions : provinceOptions;
  const province = result?.provinces.find((p) => p.id === selected);
  const selectedOption = provinceOptions.find((p) => p.id === selected);
  const name = language === "en" ? selectedOption?.name_en : selectedOption?.name;
  const level = UV_LEVELS.find((entry) => entry.id === province?.level);
  const availableCount = result?.provinces.filter((p) => p.status === "available").length ?? 0;
  const available = province?.status === "available" && province.uv_index != null;
  return <section className="uv-map-explorer" lang={language} aria-label={t("สำรวจ UV รายจังหวัด", "Explore UV by province")}>
    <div className="uv-map-source" role="group" aria-label={t("แหล่งข้อมูล UV", "UV data source")}>
      <button type="button" aria-pressed={source === "api"} onClick={() => { if (source !== "api") refresh(day, "api"); }}>{t("API · 77 พื้นที่", "API · 77 areas")}</button>
      <button type="button" aria-pressed={source === "model"} onClick={() => { if (source !== "model") refresh(day, "model"); }}>{t("โมเดลของเรา · 3 จังหวัด", "Our model · 3 provinces")}</button>
    </div>
    <div className="uv-map-toolbar">
      <div className="uv-map-days" role="group" aria-label={t("วันที่พยากรณ์", "Forecast day")}>
        {(["today", "tomorrow"] as const).map((value) => <button type="button" key={value}
          aria-pressed={day === value} onClick={() => { if (value !== day) refresh(value); }}>
          {value === "today" ? t("วันนี้", "Today") : t("พรุ่งนี้", "Tomorrow")}
        </button>)}
      </div>
      <div className="uv-map-select"><label htmlFor={selectId}>{t("เลือกจังหวัด", "Choose province")}</label>
        <select id={selectId} value={selected} onChange={(event) => setSelected(event.target.value)}>
          {options.map((p) => <option key={p.id} value={p.id}>{language === "en" ? p.name_en : p.name}</option>)}
        </select>
      </div>
      <button type="button" className="uv-map-refresh" disabled={loading} onClick={() => refresh()}>{t("โหลดข้อมูลใหม่", "Refresh data")}</button>
    </div>
    {loading && <p className="uv-map-notice" role="status">{source === "model" ? t("กำลังโหลดข้อมูล UV จากโมเดลของเรา…", "Loading UV from our model…") : t("กำลังโหลดข้อมูล UV จาก API…", "Loading UV from the API…")}</p>}
    {error && <div className="uv-map-notice" role="alert"><p>{error === "source_mismatch" ? t("แหล่งข้อมูลไม่ตรงกับที่เลือก กรุณาโหลดใหม่", "The data source does not match your selection. Refresh to try again.") : t("โหลดข้อมูล UV ไม่สำเร็จ", "Could not load UV data.")}</p><button type="button" onClick={() => refresh()}>{t("ลองอีกครั้ง", "Try again")}</button></div>}
    {result && <p className="uv-map-availability" role="status">
      {new Intl.DateTimeFormat(locale, { dateStyle: "full", timeZone: "Asia/Bangkok" }).format(new Date(`${result.date}T12:00:00+07:00`))}
      {` · ${availableCount}/${options.length} ${t("พื้นที่มีข้อมูล", "areas available")} · ${source === "model" ? t("โมเดลของเรา", "Our model") : "Open-Meteo API"}`}
      {availableCount < options.length && t(" · พื้นที่ไม่มีข้อมูลแสดงเป็นสีเทา", " · Gray areas have no available data")}
    </p>}
    <div className="uv-map-layout" aria-busy={loading}>
      <div className="uv-map-canvas uv-mission-canvas">
        <ThailandUvMap missionView language={language} provinces={result?.provinces ?? []} selectedProvinceId={selected} onSelectProvince={setSelected} provinceIds={source === "model" ? modelIds : undefined} />
        <ul className="uv-map-legend" aria-label={t("ระดับ UV", "UV levels")}>
          {UV_LEVELS.map((entry) => <li key={entry.id}><span style={{ background: entry.color }} aria-hidden="true" />{language === "en" ? entry.name_en : entry.name} <small>{entry.range}</small></li>)}
          <li><span className="uv-map-no-data" aria-hidden="true" />{t("ไม่มีข้อมูล", "No data")}</li>
        </ul>
      </div>
      <aside className="uv-map-detail" aria-live="polite" aria-atomic="true">
        <h2>{name}</h2>
        {available ? <>
          <p className="uv-map-value"><strong>{province.uv_index!.toFixed(1)}</strong><span>{t("UV ท้องฟ้าโปร่ง", "Clear-sky UV")} · {language === "en" ? level?.name_en : level?.name}</span></p>
          <p className="uv-map-advice">{province.uv_index! >= 8 ? t("หลีกเลี่ยงแดดช่วงเที่ยง และป้องกันด้วยร่มเงา เสื้อผ้า หมวก และกันแดด", "Avoid midday sun. Use shade, clothing, a hat and sunscreen for protection.") : province.uv_index! >= 3 ? t("หาที่ร่มช่วงเที่ยง และใช้เสื้อผ้า หมวก และกันแดดช่วยป้องกัน", "Seek shade around midday and use clothing, a hat and sunscreen for protection.") : t("หากอยู่กลางแจ้งนาน ให้ป้องกันแดดตามกิจกรรมของคุณ", "For longer outdoor activities, use sun protection appropriate to your activity.")}</p>
        </> : <p className="uv-map-empty">{loading ? t("กำลังโหลดค่าของจังหวัด", "Loading this province’s reading…") : province?.status === "stale" ? t("ข้อมูลเก่าเกินเกณฑ์ กรุณาลองโหลดใหม่ภายหลัง", "This reading is too old to use. Try refreshing later.") : t("ยังไม่มีค่า UV ที่พร้อมใช้สำหรับวันที่เลือก", "No UV reading is available for the selected day.")}</p>}
        {province && <dl>
          <div><dt>{t("แหล่งข้อมูล", "Data source")}</dt><dd>{province.source === "local_model" ? t("โมเดล SARIMAX ของเรา", "Our SARIMAX model") : "Open-Meteo"}</dd></div>
          <div><dt>{t("ชนิดค่า", "Reading type")}</dt><dd>{province.aggregation === "solar_noon" ? t("ค่าพยากรณ์ ณ เที่ยงสุริยะ", "Solar-noon forecast") : t("ค่าสูงสุดรายวัน", "Daily maximum")}</dd></div>
          <div><dt>{t("จุดตัวแทนจังหวัด", "Representative coordinate")}</dt><dd>{province.latitude.toFixed(4)}, {province.longitude.toFixed(4)}</dd></div>
          <div><dt>{t("อัปเดตข้อมูล", "Updated")}</dt><dd>{province.generated_at ? timeLabel(province.generated_at, language) : t("ยังไม่มีข้อมูล", "No data")}</dd></div>
          {province.data_date && <div><dt>{t("ข้อมูล TEMIS ล่าสุด", "Latest TEMIS data")}</dt><dd>{province.data_date}</dd></div>}
          {province.model_version && <div><dt>{t("รุ่นโมเดล", "Model version")}</dt><dd>{province.model_version}</dd></div>}
        </dl>}
        {province && <a href={province.source_url} target="_blank" rel="noopener noreferrer">{t("ดูแหล่งข้อมูลต้นทาง ↗", "View original data source ↗")}</a>}
        <p className="uv-map-caveat">{t("ค่า ณ จุดตัวแทน ไม่ใช่ค่าเฉลี่ยทั้งจังหวัดหรือค่าที่วัดจริง ณ จุดที่คุณอยู่ เมฆไม่ได้รับประกันว่า UV ต่ำ", "Values represent one coordinate, not a province-wide average or a measurement at your location. Clouds do not guarantee low UV.")}</p>
        {available && <a href="https://www.who.int/news-room/questions-and-answers/item/radiation-protecting-against-skin-cancer" target="_blank" rel="noopener noreferrer">{t("แนวทางป้องกันแดดจาก WHO ↗", "WHO sun-protection guidance ↗")}</a>}
      </aside>
    </div>
    <div className="uv-map-method">
      <p><strong>{source === "model" ? t("ผลทดลองจากโมเดลของเรา", "Experimental results from our model") : t("ค่าพยากรณ์จาก Open-Meteo API", "Forecasts from Open-Meteo API")}</strong> {source === "model" ? t("แสดงเฉพาะกรุงเทพฯ สงขลา และเชียงใหม่ เป็น UV ท้องฟ้าโปร่ง ณ เที่ยงสุริยะ โมเดลประเมินเทียบกับ TEMIS ยังไม่ได้ยืนยันกับ UV ที่วัดจริง", "Covers Bangkok, Songkhla and Chiang Mai only, with clear-sky UV at solar noon. Evaluated against TEMIS, not yet validated against measured UV.") : t("แสดงครบ 77 พื้นที่ เป็นค่าสูงสุดรายวันแบบท้องฟ้าโปร่งจากแหล่งเดียวกัน รวมทั้งกรุงเทพฯ สงขลา และเชียงใหม่", "Covers all 77 areas with clear-sky daily maximum values from one source, including Bangkok, Songkhla and Chiang Mai.")} {t("เลือกแหล่งข้อมูลได้จากปุ่มด้านบน ค่าระหว่างสองแหล่งยังไม่ผ่านการตรวจเทียบเพื่อใช้แทนกัน", "Select a source above. The two sources have not been validated as interchangeable.")}</p>
      <p>{t("ข้อมูล UV:", "UV data:")} <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo (CC BY 4.0)</a> {t("และ TEMIS/โมเดลของโครงการ · ขอบเขต:", "and TEMIS/project model · Boundaries:")} <a href="https://www.geoboundaries.org/api/current/gbOpen/THA/ADM1/" target="_blank" rel="noopener noreferrer">geoBoundaries / © OpenStreetMap contributors (ODbL)</a> · <a href="/assets/uv-map-provinces.json">{t("ดาวน์โหลดข้อมูลแผนที่ที่ดัดแปลง", "Download adapted map data")}</a> · <a href="/assets/uv-map-data-license.txt">{t("ที่มาและสิทธิ์ข้อมูล", "Sources and data license")}</a></p>
    </div>
  </section>;
}
