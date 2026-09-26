"use client";

import { useActionState } from "react";
import { predictTestInput } from "./actions";
import type { PredictionActionState, PredictionResponse } from "./types";
import DailyHealthDashboard from "../daily-health-dashboard";

const outdoorOptions = [
  { value: "1", label: "น้อยกว่า 1 ชั่วโมง", range: "0 ถึงน้อยกว่า 60 นาที" },
  { value: "2", label: "1–น้อยกว่า 3 ชั่วโมง", range: "60 ถึงน้อยกว่า 180 นาที" },
  { value: "3", label: "3–น้อยกว่า 4 ชั่วโมง", range: "180 ถึงน้อยกว่า 240 นาที" },
  { value: "4", label: "4 ชั่วโมงขึ้นไป", range: "ตั้งแต่ 240 นาที" },
];

function ScoreCard({ label, value, suffix, description }: { label: string; value: number | null; suffix: string; description: string }) {
  return (
    <article className="test-score-card">
      <p className="eyebrow">{label}</p>
      <strong>{value === null ? "—" : value.toFixed(1)} <small>{suffix}</small></strong>
      <p>{value === null ? "API งดทำนายข้อมูลชุดนี้" : description}</p>
    </article>
  );
}

function Results({ result }: { result: PredictionResponse }) {
  const scoreDescription = result.prediction_status === "experimental_out_of_domain"
    ? "ค่าทดลองนอกช่วงฝึก · ไม่ใช่ผลใช้งานจริง"
    : "ค่าประมาณจากโมเดลในช่วงฝึก";

  return (
    <>
      <div className="test-score-grid">
        <ScoreCard label="THIRST SCORE" value={result.predictions.thirst_score_0_10.value} suffix="/ 10" description={scoreDescription} />
        <ScoreCard label="DRYNESS SCORE" value={result.predictions.skin_dryness_score_0_10.value} suffix="/ 10" description={scoreDescription} />
      </div>
      <p className="test-model-id">โมเดล: <strong>{result.model?.model_id ?? "ไม่ระบุ"}</strong></p>
      {result.input_domain_status === "out_of_training_domain" ? (
        <p className="test-out-of-range">
          {result.prediction_status === "experimental_out_of_domain"
            ? "ผล thirst/dryness ด้านบนเป็นเพียงผลทดลองนอกช่วงฝึก; ไม่มีการแปลผลหรือคำแนะนำจากคะแนนนี้ และห้ามใช้แทนผลใช้งานจริง ยังไม่คำนวณ accuracy เพราะต้องมีผลที่ผู้ใช้สังเกตจริงมาเทียบ"
            : "ข้อมูลอยู่นอกช่วงฝึกอย่างน้อยหนึ่งค่า ระบบจึงงดทำนายในรอบนี้"}
        </p>
      ) : null}
      <DailyHealthDashboard prediction={result} />
      <details className="test-json-details">
        <summary>ดูข้อมูลตอบกลับจาก API (JSON)</summary>
        <pre>{JSON.stringify({
          local_date: result.local_date,
          model_status: result.model_status,
          input_domain_status: result.input_domain_status,
          predictions: result.predictions,
          interpretation: result.interpretation,
          next_day_predictions: result.interpretation.next_day_predictions,
          model: result.model,
          guidance: result.guidance,
          warnings: result.warnings,
        }, null, 2)}</pre>
      </details>
    </>
  );
}

export default function PredictionTestForm({ initialDate }: { initialDate: string }) {
  const initialState: PredictionActionState = {
    result: null,
    error: "",
    values: { localDate: initialDate, sleepHours: "", sleepMinutes: "", waterIntakeMl: "", outdoorChoice: "" },
  };
  const [state, formAction, isPending] = useActionState(predictTestInput, initialState);
  const result = state.result;

  return (
    <div className="prediction-test-layout">
      <section className="prediction-test-card" aria-labelledby="prediction-test-form-title">
        <div className="prediction-test-heading">
          <p className="eyebrow">TEST INPUT</p>
          <h2 id="prediction-test-form-title">ข้อมูลสำหรับทดสอบ</h2>
          <p>ลองปรับค่าแล้วส่งให้โมเดลประเมิน โดยหน้านี้ไม่บันทึกข้อมูลลงฐานข้อมูล; accuracy จะคำนวณได้เมื่อมีผลจริงแยกจากค่าทำนายเพื่อใช้เทียบ</p>
        </div>

        <form className="prediction-test-form" action={formAction}>
          <label className="test-field" htmlFor="test-date">
            <span>วันที่</span>
            <input id="test-date" name="localDate" type="date" defaultValue={state.values.localDate} max={initialDate} required />
          </label>

          <fieldset className="test-field test-sleep-field">
            <legend>ระยะเวลาการนอน</legend>
            <div className="test-sleep-inputs">
              <label htmlFor="test-sleep-hours"><span>ชั่วโมง</span><input id="test-sleep-hours" name="sleepHours" type="number" min="0" max="9" step="1" inputMode="numeric" defaultValue={state.values.sleepHours} required /></label>
              <label htmlFor="test-sleep-minutes"><span>นาที</span><input id="test-sleep-minutes" name="sleepMinutes" type="number" min="0" max="59" step="1" inputMode="numeric" defaultValue={state.values.sleepMinutes} required /></label>
            </div>
            <small>ระบบรวมเป็นนาที · ฝึกในช่วง 180–540 นาที; หน้าทดสอบจะแสดงผลทดลองนอกช่วงพร้อมเตือน ส่วนหน้าใช้งานจริงจะงดทำนาย</small>
          </fieldset>

          <label className="test-field" htmlFor="test-water-intake">
            <span>ปริมาณน้ำดื่มทั้งวัน (มล.)</span>
            <input id="test-water-intake" name="waterIntakeMl" type="number" min="0" max="20000" step="1" inputMode="numeric" placeholder="เช่น 1500" defaultValue={state.values.waterIntakeMl} required />
            <small>ป้อนค่านอกช่วง 900–1,800 มล. เพื่อดูผลทดลอง out-of-domain; ผลนี้ไม่ผ่านการรับรองและไม่ใช้ในหน้าใช้งานจริง</small>
          </label>

          <fieldset className="test-field">
            <legend>เวลาอยู่นอกบ้าน</legend>
            <div className="test-outdoor-options">
              {outdoorOptions.map((option, index) => (
                <label className={`test-outdoor-choice${state.values.outdoorChoice === option.value ? " selected" : ""}`} key={option.value}>
                  <input type="radio" name="outdoorChoice" value={option.value} required defaultChecked={state.values.outdoorChoice === option.value} />
                  <span className="test-outdoor-number">{index + 1}</span>
                  <span><strong>{option.label}</strong><small>{option.range}</small></span>
                </label>
              ))}
            </div>
          </fieldset>

          {state.error && <p className="test-form-error" role="alert">{state.error}</p>}
          <button className="primary-button prediction-test-submit" type="submit" disabled={isPending}>
            {isPending ? "กำลังทำนาย…" : "ทำนายข้อมูลนี้"}
          </button>
        </form>
      </section>

      <section className="prediction-test-card prediction-test-output" aria-labelledby="prediction-test-results-title">
        <div className="prediction-test-heading">
          <p className="eyebrow">MODEL OUTPUT</p>
          <h2 id="prediction-test-results-title">ผลการทำนาย</h2>
        </div>
        <p className="test-request-status" role="status" aria-live="polite" aria-busy={isPending}>
          {isPending ? "ส่งข้อมูลให้ Prediction API…" : result ? `รับผลแล้ว · ${result.model_status}` : "กรอกข้อมูลแล้วกดทำนายเพื่อดูผล"}
        </p>
        {result ? (
          <Results result={result} />
        ) : (
          <div className="test-output-empty" role="status">
            <span aria-hidden="true">↗</span>
            <h3>ผลจะปรากฏตรงนี้</h3>
            <p>แบบฟอร์มจะเรียกเฉพาะ Prediction API และไม่สร้างรายการบันทึกสุขภาพ</p>
          </div>
        )}
      </section>
    </div>
  );
}
