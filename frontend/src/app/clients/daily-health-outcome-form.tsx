"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useLanguage } from "@/components/language-provider";
import { Select } from "@/components/ui/select";

export default function DailyHealthOutcomeForm({ initialDate }: { initialDate: string }) {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [targetDate, setTargetDate] = useState(initialDate);
  const [energy, setEnergy] = useState("");
  const [thirst, setThirst] = useState("");
  const [dryness, setDryness] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function submitOutcome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!energy && !thirst && !dryness) {
      setError(t("เลือกอย่างน้อยหนึ่งคะแนนที่คุณสังเกตเอง", "Enter at least one score you observed."));
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
          reported_dryness_level_0_10: dryness ? Number(dryness) : null,
        }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof result?.detail === "string" ? result.detail : t("บันทึกผลที่รายงานเองไม่สำเร็จ", "Could not save the self-reported outcome."),
        );
      }
      setStatus(t("บันทึกผลที่คุณรายงานเองแล้ว · แยกจากผล prediction และยังไม่ใช้เป็นคำวินิจฉัย", "Your self-reported outcome was saved separately from predictions and is not a diagnosis."));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : t("บันทึกข้อมูลไม่สำเร็จ", "Could not save the data."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="daily-outcome-card" aria-labelledby="daily-outcome-title">
      <div>
        <p className="eyebrow">OPTIONAL SELF-REPORT</p>
        <h2 id="daily-outcome-title">{t("บันทึกผลที่สังเกตจริง", "Record observed outcomes")}</h2>
        <p>{t("ใช้เป็นผลที่คุณสังเกตเอง แยกจาก prediction; ระบบจะฝึกได้เมื่อมีคะแนน thirst และ dryness ที่รายงานจริงครบทั้งคู่ พร้อมข้อมูลไลฟ์สไตล์ของวันก่อนหน้าและ consent ฝึกโมเดล", "These are your observations, separate from predictions. Model training requires both self-reported thirst and dryness scores, the previous day's lifestyle data, and training consent.")}</p>
        <p className="training-threshold-note">{t("การสร้าง candidate ต้องมีข้อมูลที่จับคู่ครบอย่างน้อย 100 วันจากผู้ใช้ที่ยินยอมอย่างน้อย 5 คน; รุ่นถัดไปจะพิจารณาเมื่อมีข้อมูลใหม่เพิ่มอีกอย่างน้อย 25 วัน การบันทึกข้อมูลรายวันหรือคะแนน prediction เพียงอย่างเดียวไม่ใช่ label และไม่ทำให้เกิดการฝึก", "A candidate requires at least 100 complete paired days from 5 consenting users. A new version is considered after at least 25 additional days. Daily entries or predicted scores alone are not labels and do not trigger training.")}</p>
      </div>
      <form className="daily-outcome-form" onSubmit={submitOutcome}>
        <label className="tracker-field" htmlFor="outcome-date">
          <span>{t("วันที่สังเกตผล", "Date observed")}</span>
          <input
            id="outcome-date"
            type="date"
            value={targetDate}
            max={initialDate}
            required
            onChange={(event) => setTargetDate(event.target.value)}
          />
          <small>{t("หากเป็นผลเช้าวันนี้ ระบบจะนำไปจับคู่กับข้อมูลไลฟ์สไตล์ของวันก่อนหน้าเมื่อมี", "If this is a morning observation, it will be paired with the previous day's lifestyle data when available.")}</small>
        </label>
        <div className="outcome-score-fields">
          <label className="tracker-field" htmlFor="reported-energy">
            <span>{t("พลังงานที่รู้สึก (0–10)", "Perceived energy (0–10)")}</span>
            <Select
              id="reported-energy"
              value={energy}
              onChange={(val) => setEnergy(val)}
              placeholder={t("ยังไม่ระบุ", "Not specified")}
              options={[
                { value: "", label: t("ยังไม่ระบุ", "Not specified") },
                ...Array.from({ length: 11 }, (_, score) => ({
                  value: String(score),
                  label: `${score} · ${score === 0 ? t("ต่ำมาก", "Very low") : score === 10 ? t("สูงมาก", "Very high") : score}`,
                })),
              ]}
            />
          </label>
          <label className="tracker-field" htmlFor="reported-thirst">
            <span>{t("ความกระหายที่รู้สึก (0–10)", "Perceived thirst (0–10)")}</span>
            <Select
              id="reported-thirst"
              value={thirst}
              onChange={(val) => setThirst(val)}
              placeholder={t("ยังไม่ระบุ", "Not specified")}
              options={[
                { value: "", label: t("ยังไม่ระบุ", "Not specified") },
                ...Array.from({ length: 11 }, (_, score) => ({
                  value: String(score),
                  label: `${score} · ${score === 0 ? t("ไม่กระหาย", "Not thirsty") : score === 10 ? t("กระหายมาก", "Very thirsty") : score}`,
                })),
              ]}
            />
          </label>
          <label className="tracker-field" htmlFor="reported-dryness">
            <span>{t("ความรู้สึกผิวแห้งที่สังเกต (0–10)", "Observed skin dryness (0–10)")}</span>
            <Select
              id="reported-dryness"
              value={dryness}
              onChange={(val) => setDryness(val)}
              placeholder={t("ยังไม่ระบุ", "Not specified")}
              options={[
                { value: "", label: t("ยังไม่ระบุ", "Not specified") },
                ...Array.from({ length: 11 }, (_, score) => ({
                  value: String(score),
                  label: `${score} · ${score === 0 ? t("ไม่แห้ง", "Not dry") : score === 10 ? t("แห้งมาก", "Very dry") : score}`,
                })),
              ]}
            />
          </label>
        </div>
        {error && <p className="tracker-form-error" role="alert">{error}</p>}
        {status && <p className="outcome-saved" role="status" aria-live="polite">{status}</p>}
        <button className="secondary-button" type="submit" disabled={isSaving}>
          {isSaving ? t("กำลังบันทึก…", "Saving…") : t("บันทึกผลที่รายงานเอง", "Save self-reported outcome")}
        </button>
      </form>
    </section>
  );
}
