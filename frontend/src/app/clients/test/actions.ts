"use server";

import { forwardDailyHealthPrediction, todayInBangkok } from "@/lib/daily-health-prediction";
import type { PredictionActionState, PredictionResponse, PredictionTestValues } from "./types";

function isPredictionResponse(value: unknown): value is PredictionResponse {
  if (typeof value !== "object" || value === null) return false;
  const response = value as Partial<PredictionResponse>;
  return (
    typeof response.model_status === "string" &&
    typeof response.predictions?.thirst_score_0_10?.status === "string" &&
    typeof response.predictions?.skin_dryness_score_0_10?.status === "string" &&
    Array.isArray(response.guidance) &&
    Array.isArray(response.warnings)
  );
}

function readValue(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function readInteger(formData: FormData, name: string, label: string, min: number, max: number): number {
  const rawValue = readValue(formData, name);
  const value = Number(rawValue);
  if (!rawValue || !Number.isSafeInteger(value) || value < min || value > max) {
    throw new Error(`${label} ต้องเป็นจำนวนเต็มระหว่าง ${min}–${max}`);
  }
  return value;
}

function readFormValues(formData: FormData): PredictionTestValues {
  return {
    localDate: readValue(formData, "localDate"),
    sleepHours: readValue(formData, "sleepHours"),
    sleepMinutes: readValue(formData, "sleepMinutes"),
    waterIntakeMl: readValue(formData, "waterIntakeMl"),
    outdoorChoice: readValue(formData, "outdoorChoice"),
  };
}

export async function predictTestInput(
  _previousState: PredictionActionState,
  formData: FormData,
): Promise<PredictionActionState> {
  const values = readFormValues(formData);

  try {
    const date = new Date(`${values.localDate}T00:00:00.000Z`);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(values.localDate) ||
      Number.isNaN(date.valueOf()) ||
      date.toISOString().slice(0, 10) !== values.localDate
    ) {
      throw new Error("กรุณาเลือกวันที่ให้ถูกต้อง");
    }
    if (values.localDate > todayInBangkok()) throw new Error("เลือกวันที่วันนี้หรือวันที่ผ่านมาเท่านั้น");

    const sleepHours = readInteger(formData, "sleepHours", "ชั่วโมงการนอน", 0, 9);
    const sleepMinutes = readInteger(formData, "sleepMinutes", "นาทีการนอน", 0, 59);
    if (sleepHours * 60 + sleepMinutes > 540) throw new Error("เวลานอนสูงสุดที่ API รับคือ 540 นาที (9 ชั่วโมง)");
    const waterIntakeMl = readInteger(formData, "waterIntakeMl", "ปริมาณน้ำดื่ม", 0, 20_000);
    const outdoorChoice = readInteger(formData, "outdoorChoice", "ตัวเลือกเวลาอยู่นอกบ้าน", 1, 4);

    const upstream = await forwardDailyHealthPrediction(JSON.stringify({
      local_date: values.localDate,
      sleep_hours: sleepHours,
      sleep_minutes: sleepMinutes,
      water_intake_ml: waterIntakeMl,
      outdoor_exposure_choice: outdoorChoice,
    }));

    if (upstream.status < 200 || upstream.status >= 300) {
      const detail = (upstream.payload as { detail?: unknown } | null)?.detail;
      throw new Error(typeof detail === "string" ? detail : "Prediction API ทำนายข้อมูลไม่สำเร็จ");
    }
    if (!isPredictionResponse(upstream.payload)) throw new Error("Prediction API ส่งผลลัพธ์ไม่ถูกต้อง");

    return { result: upstream.payload, error: "", values };
  } catch (error) {
    return {
      result: null,
      error: error instanceof Error ? error.message : "ไม่สามารถประเมินข้อมูลได้",
      values,
    };
  }
}
