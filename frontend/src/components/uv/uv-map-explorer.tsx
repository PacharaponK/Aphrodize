"use client";

import { useEffect, useId, useState } from "react";
import { ThailandUvMap, UV_LEVELS, provinceOptions, type UvProvince } from "./thailand-uv-map";

type Day = "today" | "tomorrow";
type Source = "api" | "model";
type MapResult = { date: string; timezone: string; source: Source; provinces: UvProvince[] };

function timeLabel(value: string) {
  if (!Number.isFinite(new Date(value).getTime())) return "เวลาอัปเดตไม่พร้อม";
  return new Intl.DateTimeFormat("th-TH", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" }).format(new Date(value));
}

export function UvMapExplorer() {
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
        if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "โหลดข้อมูล UV ไม่สำเร็จ");
        if (payload.source !== source || !Array.isArray(payload.provinces)) throw new Error("แหล่งข้อมูลไม่ตรงกับที่เลือก กรุณาโหลดใหม่");
        return payload as MapResult;
      })
      .then((payload) => { if (!controller.signal.aborted) setResult(payload); })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "โหลดข้อมูล UV ไม่สำเร็จ");
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
  const name = provinceOptions.find((p) => p.id === selected)?.name;
  const level = UV_LEVELS.find((entry) => entry.id === province?.level);
  const availableCount = result?.provinces.filter((p) => p.status === "available").length ?? 0;
  const available = province?.status === "available" && province.uv_index != null;
  return <section className="uv-map-explorer" lang="th" aria-label="สำรวจ UV รายจังหวัด">
    <div className="uv-map-source" role="group" aria-label="แหล่งข้อมูล UV">
      <button type="button" aria-pressed={source === "api"} onClick={() => { if (source !== "api") refresh(day, "api"); }}>API · 77 พื้นที่</button>
      <button type="button" aria-pressed={source === "model"} onClick={() => { if (source !== "model") refresh(day, "model"); }}>โมเดลของเรา · 3 จังหวัด</button>
    </div>
    <div className="uv-map-toolbar">
      <div className="uv-map-days" role="group" aria-label="วันที่พยากรณ์">
        {(["today", "tomorrow"] as const).map((value) => <button type="button" key={value}
          aria-pressed={day === value} onClick={() => { if (value !== day) refresh(value); }}>
          {value === "today" ? "วันนี้" : "พรุ่งนี้"}
        </button>)}
      </div>
      <div className="uv-map-select"><label htmlFor={selectId}>เลือกจังหวัด</label>
        <select id={selectId} value={selected} onChange={(event) => setSelected(event.target.value)}>
          {options.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      <button type="button" className="uv-map-refresh" disabled={loading} onClick={() => refresh()}>โหลดข้อมูลใหม่</button>
    </div>
    {loading && <p className="uv-map-notice" role="status">กำลังโหลดข้อมูล UV จาก{source === "model" ? "โมเดลของเรา" : " API"}…</p>}
    {error && <div className="uv-map-notice" role="alert"><p>{error}</p><button type="button" onClick={() => refresh()}>ลองอีกครั้ง</button></div>}
    {result && <p className="uv-map-availability" role="status">
      {new Intl.DateTimeFormat("th-TH", { dateStyle: "full", timeZone: "Asia/Bangkok" }).format(new Date(`${result.date}T12:00:00+07:00`))}
      {` · มีข้อมูล ${availableCount}/${options.length} พื้นที่ · ${source === "model" ? "โมเดลของเรา" : "Open-Meteo API"}`}
      {availableCount < options.length && " · พื้นที่ไม่มีข้อมูลแสดงเป็นสีเทา"}
    </p>}
    <div className="uv-map-layout" aria-busy={loading}>
      <div className="uv-map-canvas uv-mission-canvas">
        <ThailandUvMap missionView provinces={result?.provinces ?? []} selectedProvinceId={selected} onSelectProvince={setSelected} provinceIds={source === "model" ? modelIds : undefined} />
        <ul className="uv-map-legend" aria-label="ระดับ UV">
          {UV_LEVELS.map((entry) => <li key={entry.id}><span style={{ background: entry.color }} aria-hidden="true" />{entry.name} <small>{entry.range}</small></li>)}
          <li><span className="uv-map-no-data" aria-hidden="true" />ไม่มีข้อมูล</li>
        </ul>
      </div>
      <aside className="uv-map-detail" aria-live="polite" aria-atomic="true">
        <h2>{name}</h2>
        {available ? <>
          <p className="uv-map-value"><strong>{province.uv_index!.toFixed(1)}</strong><span>UV ท้องฟ้าโปร่ง · {level?.name}</span></p>
          <p className="uv-map-advice">{province.uv_index! >= 8 ? "หลีกเลี่ยงแดดช่วงเที่ยง และป้องกันด้วยร่มเงา เสื้อผ้า หมวก และกันแดด" : province.uv_index! >= 3 ? "หาที่ร่มช่วงเที่ยง และใช้เสื้อผ้า หมวก และกันแดดช่วยป้องกัน" : "หากอยู่กลางแจ้งนาน ให้ป้องกันแดดตามกิจกรรมของคุณ"}</p>
        </> : <p className="uv-map-empty">{loading ? "กำลังโหลดค่าของจังหวัด" : province?.status === "stale" ? "ข้อมูลเก่าเกินเกณฑ์ กรุณาลองโหลดใหม่ภายหลัง" : "ยังไม่มีค่า UV ที่พร้อมใช้สำหรับวันที่เลือก"}</p>}
        {province && <dl>
          <div><dt>แหล่งข้อมูล</dt><dd>{province.source === "local_model" ? "โมเดล SARIMAX ของเรา" : "Open-Meteo"}</dd></div>
          <div><dt>ชนิดค่า</dt><dd>{province.aggregation === "solar_noon" ? "ค่าพยากรณ์ ณ เที่ยงสุริยะ" : "ค่าสูงสุดรายวัน"}</dd></div>
          <div><dt>จุดตัวแทนจังหวัด</dt><dd>{province.latitude.toFixed(4)}, {province.longitude.toFixed(4)}</dd></div>
          <div><dt>อัปเดตข้อมูล</dt><dd>{province.generated_at ? timeLabel(province.generated_at) : "ยังไม่มีข้อมูล"}</dd></div>
          {province.data_date && <div><dt>ข้อมูล TEMIS ล่าสุด</dt><dd>{province.data_date}</dd></div>}
          {province.model_version && <div><dt>รุ่นโมเดล</dt><dd>{province.model_version}</dd></div>}
        </dl>}
        {province && <a href={province.source_url} target="_blank" rel="noopener noreferrer">ดูแหล่งข้อมูลต้นทาง ↗</a>}
        <p className="uv-map-caveat">ค่า ณ จุดตัวแทน ไม่ใช่ค่าเฉลี่ยทั้งจังหวัดหรือค่าที่วัดจริง ณ จุดที่คุณอยู่ เมฆไม่ได้รับประกันว่า UV ต่ำ</p>
        {available && <a href="https://www.who.int/news-room/questions-and-answers/item/radiation-protecting-against-skin-cancer" target="_blank" rel="noopener noreferrer">แนวทางป้องกันแดดจาก WHO ↗</a>}
      </aside>
    </div>
    <div className="uv-map-method">
      <p><strong>{source === "model" ? "ผลทดลองจากโมเดลของเรา" : "ค่าพยากรณ์จาก Open-Meteo API"}</strong> {source === "model" ? "แสดงเฉพาะกรุงเทพฯ สงขลา และเชียงใหม่ เป็น UV ท้องฟ้าโปร่ง ณ เที่ยงสุริยะ โมเดลประเมินเทียบกับ TEMIS ยังไม่ได้ยืนยันกับ UV ที่วัดจริง" : "แสดงครบ 77 พื้นที่ เป็นค่าสูงสุดรายวันแบบท้องฟ้าโปร่งจากแหล่งเดียวกัน รวมทั้งกรุงเทพฯ สงขลา และเชียงใหม่"} เลือกแหล่งข้อมูลได้จากปุ่มด้านบน ค่าระหว่างสองแหล่งยังไม่ผ่านการตรวจเทียบเพื่อใช้แทนกัน</p>
      <p>ข้อมูล UV: <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo (CC BY 4.0)</a> และ TEMIS/โมเดลของโครงการ · ขอบเขต: <a href="https://www.geoboundaries.org/api/current/gbOpen/THA/ADM1/" target="_blank" rel="noopener noreferrer">geoBoundaries / © OpenStreetMap contributors (ODbL)</a> · <a href="/assets/uv-map-provinces.json">ดาวน์โหลดข้อมูลแผนที่ที่ดัดแปลง</a> · <a href="/assets/uv-map-data-license.txt">ที่มาและสิทธิ์ข้อมูล</a></p>
    </div>
  </section>;
}
