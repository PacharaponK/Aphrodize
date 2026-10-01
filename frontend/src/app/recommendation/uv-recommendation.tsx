"use client";

import { useEffect, useState } from "react";
import { Select } from "@/components/ui/select";

type City = "bangkok" | "songkhla" | "chiang_mai";
type ForecastDay = {
  date: string;
  uv_index_clear_sky: number;
  value_kind: string;
  level: string;
  priority: "avoid_midday" | "seek_midday_shade" | "routine";
  weather: { cloud_cover_percent: number | null; rain_probability_percent: number | null } | null;
};
type Result = {
  data_date: string;
  generated_at: string;
  model_version: string;
  days: ForecastDay[];
  advice: { source_url: string };
  products: { brand: string; name: string; spf: number; water_resistant_minutes: number | null; source_url: string }[];
};

const cityNames: Record<City, string> = { bangkok: "กรุงเทพมหานคร", songkhla: "สงขลา", chiang_mai: "เชียงใหม่" };
const levels: Record<string, string> = { low: "ต่ำ", moderate: "ปานกลาง", high: "สูง", very_high: "สูงมาก", extreme: "สูงสุดขีด" };

export function UvRecommendation() {
  const [city, setCity] = useState<City>("bangkok");
  const [dayIndex, setDayIndex] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/uv/recommendation?city=${city}`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "โหลดข้อมูล UV ไม่สำเร็จ");
        return payload as Result;
      })
      .then(setResult)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "โหลดข้อมูล UV ไม่สำเร็จ");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [city, attempt]);

  const day = result?.days[dayIndex];
  function reload() {
    setLoading(true);
    setResult(null);
    setError("");
    setAttempt((value) => value + 1);
  }
  const dateLabel = day && new Intl.DateTimeFormat("th-TH", { dateStyle: "full", timeZone: "Asia/Bangkok" }).format(new Date(`${day.date}T12:00:00+07:00`));
  return <section className="page-content workspace-panel uv-page">
    <div className="uv-intro"><p className="eyebrow">ข้อมูลสำหรับวางแผนกลางแจ้ง</p><h2>เลือกพื้นที่และวันที่</h2><p>ประมาณการ UV ตอนเที่ยงภายใต้ท้องฟ้าโปร่ง พร้อมวิธีป้องกันแสงแดด</p></div>
      <div className="uv-controls">
        <label htmlFor="uv-city">พื้นที่</label>
        <Select
          id="uv-city"
          value={city}
          onChange={(val) => {
            setLoading(true);
            setResult(null);
            setError("");
            setCity(val as City);
            setDayIndex(0);
          }}
          options={Object.entries(cityNames).map(([value, label]) => ({
            value,
            label,
          }))}
        />
      <div className="uv-day-buttons" role="group" aria-label="วันที่พยากรณ์">
        {["วันนี้", "พรุ่งนี้"].map((label, index) => <button key={label} type="button" aria-pressed={dayIndex === index} onClick={() => setDayIndex(index)}>{label}</button>)}
      </div>
    </div>
    {loading && <p role="status" className="uv-notice">กำลังโหลดข้อมูล UV…</p>}
    {error && <div role="alert" className="uv-notice"><p>ยังแสดงค่าพยากรณ์ไม่ได้: {error}</p><button type="button" onClick={reload}>ลองอีกครั้ง</button></div>}
    {day && result && <>
      <article className="uv-summary" aria-label={`ระดับ UV ของ${cityNames[city]}`}>
        <div><p className="eyebrow">{cityNames[city]} · {dateLabel}</p><h3>UV ท้องฟ้าโปร่ง</h3><p>ค่าประมาณ ณ เที่ยงสุริยะ</p></div>
        <div className="uv-reading"><strong>{day.uv_index_clear_sky.toFixed(1)}</strong><span>ระดับ{levels[day.level] ?? day.level}</span></div>
      </article>
      <p className="uv-caveat">ตัวเลขนี้เป็นค่า UV ภายใต้ท้องฟ้าโปร่ง ไม่ใช่ค่า UV จริง ณ จุดที่คุณอยู่ เมฆไม่ได้รับประกันว่า UV ต่ำ</p>
      <p className="uv-priority">{day.priority === "avoid_midday" ? "ควรหลีกเลี่ยงการอยู่กลางแจ้งช่วงเที่ยง และเพิ่มการป้องกันด้วยร่มเงา เสื้อผ้า หมวก และกันแดด" : day.priority === "seek_midday_shade" ? "ควรหาที่ร่มในช่วงเที่ยง พร้อมใช้เสื้อผ้า หมวก และกันแดด" : "หากอยู่นอกอาคารนาน ให้ป้องกันแดดตามกิจกรรมและสภาพผิว"}</p>
      <div className="uv-grid">
        <article className="uv-panel"><h3>วิธีป้องกัน</h3><ul>
          <li>ใช้กันแดดป้องกัน UVA/UVB (broad-spectrum) SPF 30 ขึ้นไป ทาให้ทั่วผิวที่เปิดรับแสงก่อนออกกลางแจ้งตามฉลาก</li>
          <li>ทาซ้ำอย่างน้อยทุก 2 ชั่วโมงขณะอยู่กลางแจ้ง และหลังว่ายน้ำ เหงื่อออก หรือเช็ดตัว ตามคำแนะนำบนฉลาก</li>
          <li>หาที่ร่ม สวมเสื้อผ้าป้องกัน หมวกปีกกว้าง และแว่นกันแดด โดยเฉพาะช่วงเที่ยง</li>
        </ul><a href={result.advice.source_url} target="_blank" rel="noopener noreferrer">ดูคำแนะนำจาก WHO ↗</a></article>
        <article className="uv-panel"><h3>สภาพอากาศประกอบ</h3>{day.weather ? <><p>เมฆปกคลุมราว {day.weather.cloud_cover_percent ?? "–"}% เวลา 12:00 น.</p><p>โอกาสฝน {day.weather.rain_probability_percent ?? "–"}%</p><p className="uv-secondary">ข้อมูลอากาศจาก Open-Meteo ไม่ได้นำมาลดค่า UV</p></> : <p>ข้อมูลสภาพอากาศไม่พร้อม คำแนะนำกันแดดยังใช้ได้</p>}</article>
      </div>
      <article className="uv-panel"><h3>ผลิตภัณฑ์ที่ตรวจทานแล้ว</h3>{result.products.length ? <div className="uv-products">{result.products.map((product) => <div key={product.source_url} className="uv-product"><strong>{product.brand} {product.name}</strong><span>SPF {product.spf} · Broad-spectrum{product.water_resistant_minutes ? ` · ทนน้ำ ${product.water_resistant_minutes} นาทีตามฉลาก` : ""}</span><a href={product.source_url} target="_blank" rel="noopener noreferrer">ตรวจสอบข้อมูลผลิตภัณฑ์ ↗</a></div>)}</div> : <p>ยังไม่มีผลิตภัณฑ์กันแดดที่ผ่านการตรวจทาน เลือกชนิด broad-spectrum SPF 30 ขึ้นไปตามฉลาก</p>}</article>
      <p className="uv-secondary">ข้อมูล TEMIS ล่าสุด: {result.data_date} · สร้างผล: {new Date(result.generated_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })} · {day.value_kind} · {result.model_version}</p>
    </>}
  </section>;
}
