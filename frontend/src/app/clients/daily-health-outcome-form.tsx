"use client";

import { useState } from "react";
import type { FormEvent } from "react";

export default function DailyHealthOutcomeForm({ initialDate }: { initialDate: string }) {
  const [targetDate, setTargetDate] = useState(initialDate);
  const [energy, setEnergy] = useState("");
  const [thirst, setThirst] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function submitOutcome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!energy && !thirst) {
      setError("เลือกอย่างน้อยหนึ่งคะแนนที่คุณสังเกตเอง");
      return;
    }
    setError("");
    setStatus("");
    setIsSaving(true);
    try {
      const response = await fetch("/api/daily-health/outcomes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          consent_to_store: true,
          target_date: targetDate,
          reported_energy_level_0_10: energy ? Number(energy) : null,
          reported_thirst_level_0_10: thirst ? Number(thirst) : null,
        }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof result?.detail === "string" ? result.detail : "บันทึกผลที่รายงานเองไม่สำเร็จ",
        );
      }
      setStatus("บันทึกผลที่คุณรายงานเองแล้ว · แยกจากผล prediction และยังไม่ใช้เป็นคำวินิจฉัย");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "บันทึกข้อมูลไม่สำเร็จ");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="daily-outcome-card" aria-labelledby="daily-outcome-title">
      <div>
        <p className="eyebrow">OPTIONAL SELF-REPORT</p>
        <h2 id="daily-outcome-title">บันทึกผลที่สังเกตจริง</h2>
        <p>ใช้เป็น label แยกต่างหากสำหรับประเมินโมเดลในอนาคต ไม่ใช่ค่าที่โมเดลทำนาย</p>
      </div>
      <form className="daily-outcome-form" onSubmit={submitOutcome}>
        <label className="tracker-field" htmlFor="outcome-date">
          <span>วันที่สังเกตผล</span>
          <input
            id="outcome-date"
            type="date"
            value={targetDate}
            max={initialDate}
            required
            onChange={(event) => setTargetDate(event.target.value)}
          />
          <small>หากเป็นผลเช้าวันนี้ ระบบจะนำไปจับคู่กับข้อมูลไลฟ์สไตล์ของวันก่อนหน้าเมื่อมี</small>
        </label>
        <div className="outcome-score-fields">
          <label className="tracker-field" htmlFor="reported-energy">
            <span>พลังงานที่รู้สึก (0–10)</span>
            <select id="reported-energy" value={energy} onChange={(event) => setEnergy(event.target.value)}>
              <option value="">ยังไม่ระบุ</option>
              {Array.from({ length: 11 }, (_, score) => (
                <option key={score} value={score}>{score} · {score === 0 ? "ต่ำมาก" : score === 10 ? "สูงมาก" : ""}</option>
              ))}
            </select>
          </label>
          <label className="tracker-field" htmlFor="reported-thirst">
            <span>ความกระหายที่รู้สึก (0–10)</span>
            <select id="reported-thirst" value={thirst} onChange={(event) => setThirst(event.target.value)}>
              <option value="">ยังไม่ระบุ</option>
              {Array.from({ length: 11 }, (_, score) => (
                <option key={score} value={score}>{score} · {score === 0 ? "ไม่กระหาย" : score === 10 ? "กระหายมาก" : ""}</option>
              ))}
            </select>
          </label>
        </div>
        {error && <p className="tracker-form-error" role="alert">{error}</p>}
        {status && <p className="outcome-saved" role="status" aria-live="polite">{status}</p>}
        <button className="secondary-button" type="submit" disabled={isSaving}>
          {isSaving ? "กำลังบันทึก…" : "บันทึกผลที่รายงานเอง"}
        </button>
      </form>
    </section>
  );
}
