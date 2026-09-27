"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";

type OutdoorChoice = "under_1_hour" | "1_to_under_3_hours" | "3_to_under_4_hours" | "4_hours_or_more";

type ScorePrediction = { value: number | null; status: "predicted" | "not_available" };
type PredictionResponse = {
  model_status: string;
  model?: { model_id?: string };
  predictions: {
    thirst_score_0_10: ScorePrediction;
    skin_dryness_score_0_10: ScorePrediction;
  };
  guidance: string[];
  warnings: string[];
};

type DailyEntry = {
  date: string;
  sleepHours: number;
  sleepMinutes: number;
  sleepDurationMinutes: number;
  waterIntakeMl: number;
  outdoorChoice: OutdoorChoice;
};

type FormValues = {
  date: string;
  sleepHours: string;
  sleepMinutes: string;
  waterIntakeMl: string;
  outdoorChoice: OutdoorChoice | "";
  consentToStore: boolean;
};

type StorageStatus = "idle" | "saving" | "saved" | "failed";

const outdoorOptions: { value: OutdoorChoice; apiChoice: number; label: string; range: string }[] = [
  { value: "under_1_hour", apiChoice: 1, label: "น้อยกว่า 1 ชั่วโมง", range: "0 ถึงน้อยกว่า 60 นาที" },
  { value: "1_to_under_3_hours", apiChoice: 2, label: "1–2 ชั่วโมง", range: "60 ถึงน้อยกว่า 180 นาที" },
  { value: "3_to_under_4_hours", apiChoice: 3, label: "3–น้อยกว่า 4 ชั่วโมง", range: "180 ถึงน้อยกว่า 240 นาที" },
  { value: "4_hours_or_more", apiChoice: 4, label: "4 ชั่วโมงขึ้นไป", range: "ตั้งแต่ 240 นาที" },
];

const emptyForm: FormValues = {
  date: "",
  sleepHours: "",
  sleepMinutes: "",
  waterIntakeMl: "",
  outdoorChoice: "",
  consentToStore: false,
};

function localDateValue(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("th-TH", {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function ScoreMethodDetails() {
  return (
    <details className="score-method-details">
      <summary>ดูวิธีคำนวณคะแนนและแหล่งอ้างอิง</summary>
      <div className="score-method-content">
        <section aria-labelledby="predicted-score-method-title">
          <h3 id="predicted-score-method-title">Thirst และ dryness · ผลจากโมเดล</h3>
          <p>API ส่งเวลานอนรวม (S), น้ำดื่ม (W) และตัวเลือกเวลาอยู่นอกบ้านเข้า RandomForestRegressor แบบหลายผลลัพธ์ โมเดลเฉลี่ยค่าจากต้นไม้ 300 ต้น แล้วจำกัดคะแนนไว้ 0–10 และปัดทศนิยม 1 ตำแหน่ง</p>
          <p>ป้ายคะแนนที่ใช้ฝึกเป็นข้อมูลสังเคราะห์ โดยสร้างจากกฎตัวอย่างเหล่านี้ก่อนฝึกโมเดล ไม่ใช่สูตรแพทย์:</p>
          <code>thirst = clip(round(1.5 + max(0, (420 − S) ÷ 80) + max(0, (1500 − W) ÷ 200), 1), 0, 10)</code>
          <code className="dryness-formula">{`skin_dryness_score_0_10 = round(U(min, max), 1)
(min, max) =
  (1, 3)   if S ≥ 420 and W ≥ 1500
  (4, 6)   if S ≥ 420 and W < 1500
  (7, 10)  if S < 360 and W < 1500
  (2, 7)   otherwise`}</code>
          <p>U(min, max) คือการสุ่มค่าแบบ uniform ในช่วงที่ตรงเงื่อนไข แล้วปัดทศนิยม 1 ตำแหน่ง; สูตรนี้ใช้สร้าง target สำหรับฝึก ส่วนโมเดลจริงเรียนรู้ความสัมพันธ์จาก target เหล่านี้แล้วทำนายคะแนน</p>
          <p>ค่า 420 นาทีและ 1,500 มล. เป็นจุดอ้างอิงในการจำลองชุดข้อมูล ไม่ใช่เกณฑ์ทางการแพทย์ และข้อมูลน้ำในฟอร์มไม่ใช่ total water จากอาหารและเครื่องดื่มทั้งหมด ตัวเลือกเวลาอยู่นอกบ้านเป็น feature ของโมเดล แต่ไม่ได้อยู่ในกฎสร้างป้าย thirst/dryness จึงใช้สรุปเหตุและผลหรือประเมินรังสี UV ไม่ได้</p>
          <div className="score-method-references" aria-label="แหล่งอ้างอิง">
            <a href="https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html" target="_blank" rel="noreferrer">scikit-learn: วิธีทำงานของ RandomForestRegressor</a>
            <a href="https://nap.nationalacademies.org/read/10925/chapter/2" target="_blank" rel="noreferrer">National Academies: น้ำรวมจากน้ำดื่ม เครื่องดื่ม และอาหาร</a>
            <a href="https://doi.org/10.1111/srt.12454" target="_blank" rel="noreferrer">Akdeniz et al. (2018): ทบทวนหลักฐานเรื่องน้ำกับความชุ่มชื้นผิว</a>
          </div>
        </section>
      </div>
    </details>
  );
}

export default function DailyHealthTracker() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [today, setToday] = useState("");
  const [form, setForm] = useState<FormValues>(emptyForm);
  const [entry, setEntry] = useState<DailyEntry | null>(null);
  const [formError, setFormError] = useState("");
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [predictionError, setPredictionError] = useState("");
  const [isPredicting, setIsPredicting] = useState(false);
  const [storageStatus, setStorageStatus] = useState<StorageStatus>("idle");
  const [storageMessage, setStorageMessage] = useState("");
  const predictionRequestId = useRef(0);

  function openDialog() {
    const currentDate = localDateValue();
    setToday(currentDate);
    setForm((current) => ({ ...current, date: current.date || currentDate }));
    setFormError("");
    dialogRef.current?.showModal();
  }

  function closeDialog() {
    dialogRef.current?.close();
  }

  function updateForm<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveEntry(dailyEntry: DailyEntry, predictionResult: PredictionResponse | null) {
    setStorageStatus("saving");
    setStorageMessage("");
    try {
      const thirstScore = predictionResult?.predictions.thirst_score_0_10.value ?? null;
      const drynessScore = predictionResult?.predictions.skin_dryness_score_0_10.value ?? null;
      const hasScores = thirstScore !== null && drynessScore !== null;
      const response = await fetch("/api/daily-health/entries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          consent_to_store: true,
          local_date: dailyEntry.date,
          timezone: "Asia/Bangkok",
          sleep_duration_minutes: dailyEntry.sleepDurationMinutes,
          water_intake_ml: dailyEntry.waterIntakeMl,
          outdoor_exposure_choice: outdoorOptions.find((option) => option.value === dailyEntry.outdoorChoice)?.apiChoice,
          prediction: predictionResult
            ? {
                thirst_score_0_10: thirstScore,
                dryness_score_0_10: drynessScore,
                prediction_status: hasScores ? "predicted" : "not_available",
                model_id: predictionResult.model?.model_id ?? null,
              }
            : null,
        }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(typeof result?.detail === "string" ? result.detail : "ไม่สามารถบันทึกข้อมูลลงฐานข้อมูลได้");
      }
      setStorageStatus("saved");
      setStorageMessage("บันทึกข้อมูลรายวันนี้ลงฐานข้อมูลแล้ว · คะแนนจากโมเดลยังไม่ถือเป็นป้ายกำกับจริงสำหรับ train");
    } catch (error) {
      setStorageStatus("failed");
      setStorageMessage(error instanceof Error ? error.message : "บันทึกข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง");
    }
  }

  async function submitEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hours = Number(form.sleepHours);
    const minutes = Number(form.sleepMinutes);
    const water = Number(form.waterIntakeMl);

    if (!form.date || !form.sleepHours || !form.sleepMinutes || !form.waterIntakeMl || !form.outdoorChoice) {
      setFormError("กรุณากรอกข้อมูลให้ครบทุกช่องก่อนดูสรุป");
      return;
    }
    if (hours === 24 && minutes > 0) {
      setFormError("ถ้ากรอกเวลานอน 24 ชั่วโมง นาทีต้องเป็น 0");
      return;
    }
    if (hours * 60 + minutes > 540) {
      setFormError("ระยะเวลานอนสูงสุดที่บันทึกได้คือ 540 นาที (9 ชั่วโมง)");
      return;
    }
    if (form.date > today) {
      setFormError("เลือกวันที่วันนี้หรือวันที่ผ่านมาเท่านั้น");
      return;
    }
    if (!form.consentToStore) {
      setFormError("กรุณายินยอมให้บันทึกข้อมูลรายวันก่อนส่งข้อมูล");
      return;
    }

    const dailyEntry = {
      date: form.date,
      sleepHours: hours,
      sleepMinutes: minutes,
      sleepDurationMinutes: hours * 60 + minutes,
      waterIntakeMl: water,
      outdoorChoice: form.outdoorChoice,
    } satisfies DailyEntry;
    const selectedChoice = outdoorOptions.find((option) => option.value === form.outdoorChoice);
    const requestId = ++predictionRequestId.current;
    setEntry(dailyEntry);
    setPrediction(null);
    setPredictionError("");
    setIsPredicting(true);
    setStorageStatus("saving");
    setStorageMessage("กำลังบันทึกข้อมูลรายวันลงฐานข้อมูล");
    setForm((current) => ({ ...current, consentToStore: false }));
    setFormError("");
    closeDialog();

    let predictionResult: PredictionResponse | null = null;
    try {
      const response = await fetch("/api/daily-health/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          local_date: dailyEntry.date,
          sleep_hours: dailyEntry.sleepHours,
          sleep_minutes: dailyEntry.sleepMinutes,
          water_intake_ml: dailyEntry.waterIntakeMl,
          outdoor_exposure_choice: selectedChoice?.apiChoice,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(typeof result.detail === "string" ? result.detail : "ไม่สามารถเรียกโมเดลได้");
      }
      predictionResult = result as PredictionResponse;
      if (requestId === predictionRequestId.current) setPrediction(predictionResult);
    } catch (error) {
      if (requestId === predictionRequestId.current) {
        setPredictionError(error instanceof Error ? error.message : "ไม่สามารถเชื่อมต่อ Prediction API ได้");
      }
    }
    await saveEntry(dailyEntry, predictionResult);
    if (requestId === predictionRequestId.current) setIsPredicting(false);
  }

  const selectedOutdoor = outdoorOptions.find((option) => option.value === entry?.outdoorChoice);

  return (
    <div className="clients-tracker">
      <section className="daily-entry-card" aria-labelledby="daily-entry-title">
        <div className="daily-entry-copy">
          <p className="eyebrow">บันทึกประจำวัน</p>
          <h2 id="daily-entry-title">ข้อมูลสุขภาพรายวัน</h2>
          <p>วันที่จะตั้งเป็นวันนี้ให้อัตโนมัติ และสามารถเลือกวันที่ย้อนหลังได้</p>
        </div>
        <button className="primary-button daily-open-button" type="button" onClick={openDialog}>
          {entry ? "แก้ไขข้อมูลที่กรอก" : "＋ กรอกข้อมูลรายวัน"}
        </button>
      </section>

      <dialog className="daily-entry-dialog" ref={dialogRef} aria-labelledby="daily-dialog-title">
        <button className="close-button" type="button" onClick={closeDialog} aria-label="ปิดแบบฟอร์ม">×</button>
        <p className="eyebrow">DAILY CHECK-IN</p>
        <h2 id="daily-dialog-title">กรอกข้อมูลสุขภาพรายวัน</h2>
        <p className="dialog-description">กรอกค่าที่คุณสังเกตหรือบันทึกได้ ข้อมูลนี้ไม่ใช่ผลวินิจฉัย</p>

        <form className="daily-entry-form" onSubmit={submitEntry}>
          <label className="tracker-field" htmlFor="entry-date">
            <span>วันที่</span>
            <input
              id="entry-date"
              type="date"
              value={form.date}
              max={today || undefined}
              required
              onChange={(event) => updateForm("date", event.target.value)}
            />
            <small>ค่าเริ่มต้นคือวันที่ปัจจุบันของอุปกรณ์</small>
          </label>

          <fieldset className="tracker-field sleep-field">
            <legend>ระยะเวลาการนอน</legend>
            <div className="sleep-inputs">
              <label htmlFor="sleep-hours"><span>ชั่วโมง</span><input id="sleep-hours" type="number" min="0" max="24" step="1" inputMode="numeric" placeholder="เช่น 7" required value={form.sleepHours} onChange={(event) => updateForm("sleepHours", event.target.value)} /></label>
              <label htmlFor="sleep-minutes"><span>นาที</span><input id="sleep-minutes" type="number" min="0" max="59" step="1" inputMode="numeric" placeholder="เช่น 30" required value={form.sleepMinutes} onChange={(event) => updateForm("sleepMinutes", event.target.value)} /></label>
            </div>
            <small>ระบบรวมเป็นนาทีด้วยสูตร ชั่วโมง × 60 + นาที</small>
          </fieldset>

          <label className="tracker-field" htmlFor="water-intake">
            <span>ปริมาณน้ำดื่ม (มล.)</span>
            <input id="water-intake" type="number" min="0" max="20000" step="1" inputMode="numeric" placeholder="เช่น 1500" required value={form.waterIntakeMl} onChange={(event) => updateForm("waterIntakeMl", event.target.value)} />
            <small>กรอกยอดสะสมทั้งวัน; โมเดลฝึกด้วยช่วง 900–1,800 มล. ถ้ากรอกยอดระหว่างวันอาจอยู่นอกช่วงฝึก</small>
          </label>

          <fieldset className="tracker-field outdoor-field">
            <legend>เวลาอยู่นอกบ้าน</legend>
            <div className="outdoor-options">
              {outdoorOptions.map((option, index) => (
                <label className={`outdoor-choice${form.outdoorChoice === option.value ? " selected" : ""}`} key={option.value}>
                  <input type="radio" name="outdoor-choice" value={option.value} checked={form.outdoorChoice === option.value} required onChange={() => updateForm("outdoorChoice", option.value)} />
                  <span className="outdoor-choice-number">{index + 1}</span>
                  <span className="outdoor-choice-text"><strong>{option.label}</strong><small>{option.range}</small></span>
                </label>
              ))}
            </div>
            <small className="range-note">กำหนดเส้นแบ่งให้ไม่ซ้อนกัน: ตัวเลือก 2 ครอบคลุม 1 ถึงน้อยกว่า 3 ชั่วโมง และตัวเลือก 4 เริ่มตั้งแต่ 4 ชั่วโมง</small>
          </fieldset>

          <label className="daily-data-consent">
            <input type="checkbox" required checked={form.consentToStore} onChange={(event) => updateForm("consentToStore", event.target.checked)} />
            <span>ยินยอมให้บันทึกข้อมูลสุขภาพรายวันนี้ในฐานข้อมูลเพื่อใช้กับประวัติและพัฒนาระบบต่อ โดยเข้าใจว่าคะแนนจากโมเดลเป็นเพียงค่าคาดการณ์ ไม่ใช่คะแนนจริงสำหรับใช้ train</span>
          </label>

          {formError && <p className="tracker-form-error" role="alert">{formError}</p>}
          <div className="tracker-form-actions">
            <button className="secondary-button" type="button" onClick={closeDialog}>ยกเลิก</button>
            <button className="primary-button" type="submit">บันทึกและแสดงผล</button>
          </div>
        </form>
      </dialog>

      <section className="tracker-results" aria-labelledby="tracker-results-title">
        <div className="tracker-section-heading">
          <div>
            <p className="eyebrow">MODEL RESULTS</p>
            <h2 id="tracker-results-title">ผลสรุปและการพยากรณ์</h2>
          </div>
          <span className={`model-status${prediction ? " model-status-ready" : ""}`}>
            {isPredicting ? "กำลังประเมินข้อมูล" : prediction ? "ได้รับผลจาก Prediction API" : "พร้อมทำนายเมื่อส่งข้อมูล"}
          </span>
        </div>

        {entry ? (
          <>
            <p className="entry-date-line" role="status" aria-live="polite">สรุปข้อมูลวันที่ {displayDate(entry.date)}</p>
            <div className="tracker-metric-grid">
              <article className="tracker-metric duration-metric">
                <p className="eyebrow">ระยะเวลานอนที่คำนวณได้</p>
                <strong>{entry.sleepHours} ชม. {entry.sleepMinutes} นาที</strong>
                <p>รวม {entry.sleepDurationMinutes.toLocaleString("th-TH")} นาที</p>
              </article>
              <article className="tracker-metric pending-metric">
                <p className="eyebrow">THIRST SCORE</p>
                <strong>{isPredicting ? "…" : prediction?.predictions.thirst_score_0_10.value?.toFixed(1) ?? "—"} <small>/ 10</small></strong>
                <p>{prediction?.predictions.thirst_score_0_10.status === "not_available" ? "อยู่นอกช่วงข้อมูลฝึก จึงงดทำนาย" : prediction ? "ค่าประมาณจากโมเดล synthetic regression" : "รอผลจาก Prediction API"}</p>
              </article>
              <article className="tracker-metric pending-metric">
                <p className="eyebrow">DRYNESS SCORE</p>
                <strong>{isPredicting ? "…" : prediction?.predictions.skin_dryness_score_0_10.value?.toFixed(1) ?? "—"} <small>/ 10</small></strong>
                <p>{prediction?.predictions.skin_dryness_score_0_10.status === "not_available" ? "อยู่นอกช่วงข้อมูลฝึก จึงงดทำนาย" : prediction ? "ค่าประมาณจากโมเดล synthetic regression" : "รอผลจาก Prediction API"}</p>
              </article>
            </div>
            <div className="entry-summary" aria-label="ข้อมูลที่กรอก">
              <span>น้ำดื่ม <strong>{entry.waterIntakeMl.toLocaleString("th-TH")} มล.</strong></span>
              <span>เวลาอยู่นอกบ้าน <strong>{selectedOutdoor?.label}</strong></span>
            </div>
            <p className={`storage-status storage-status-${storageStatus}`} role="status" aria-live="polite">
              {storageMessage || (storageStatus === "saved" ? "บันทึกข้อมูลรายวันนี้ลงฐานข้อมูลแล้ว" : "")}
            </p>
            {storageStatus === "failed" && (
              <button className="secondary-button storage-retry" type="button" onClick={() => void saveEntry(entry, prediction)}>
                ลองบันทึกอีกครั้ง
              </button>
            )}
          </>
        ) : (
          <div className="tracker-empty-state">
            <span className="tracker-empty-icon" aria-hidden="true">＋</span>
            <h3>เริ่มจากบันทึกข้อมูลของวันนี้</h3>
            <p>หลังส่งแบบฟอร์ม API จะใช้ระยะเวลานอน น้ำดื่ม และเวลาอยู่นอกบ้านเพื่อประเมินคะแนน thirst/dryness</p>
          </div>
        )}

        {predictionError && <p className="prediction-error" role="alert">{predictionError}</p>}
        {prediction?.guidance.length ? (
          <section className="prediction-guidance" aria-labelledby="prediction-guidance-title" aria-live="polite">
            <h3 id="prediction-guidance-title">ข้อแนะนำที่เกี่ยวข้อง</h3>
            <ul>{prediction.guidance.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
        ) : null}
        <ScoreMethodDetails />
      </section>

    </div>
  );
}
