"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import DailyHealthDashboard from "./daily-health-dashboard";
import DailyHealthOutcomeForm from "./daily-health-outcome-form";
import type { AgeBand, DailyHealthProfile, PredictionResponse, SmokingStatus } from "@/lib/daily-health-types";
import { useLanguage } from "@/components/language-provider";

type OutdoorChoice = "under_1_hour" | "1_to_under_3_hours" | "3_to_under_4_hours" | "4_hours_or_more";

type MenstruationChoice = "yes" | "no" | "";

type DailyEntry = {
  date: string;
  sleepHours: number;
  sleepMinutes: number;
  sleepDurationMinutes: number;
  waterIntakeMl: number;
  outdoorChoice: OutdoorChoice;
  modelTrainingConsent: boolean;
  personalizationConsent: boolean;
  ageGuidanceConsent: boolean;
  ageBand: AgeBand | null;
  smokingStatus: SmokingStatus | null;
  currentlyMenstruating: boolean | null;
};

type FormValues = {
  date: string;
  sleepHours: string;
  sleepMinutes: string;
  waterIntakeMl: string;
  outdoorChoice: OutdoorChoice | "";
  consentToStore: boolean;
  modelTrainingConsent: boolean;
  personalizationConsent: boolean;
  ageGuidanceConsent: boolean;
  ageBand: AgeBand | "";
  smokingStatus: SmokingStatus | "";
  menstruationChoice: MenstruationChoice;
};

type StorageStatus = "idle" | "saving" | "saved" | "failed";

const outdoorOptions: { value: OutdoorChoice; apiChoice: number; label: string; range: string }[] = [
  { value: "under_1_hour", apiChoice: 1, label: "น้อยกว่า 1 ชั่วโมง", range: "0 ถึงน้อยกว่า 60 นาที" },
  { value: "1_to_under_3_hours", apiChoice: 2, label: "1–น้อยกว่า 3 ชั่วโมง", range: "60 ถึงน้อยกว่า 180 นาที" },
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
  modelTrainingConsent: false,
  personalizationConsent: false,
  ageGuidanceConsent: false,
  ageBand: "",
  smokingStatus: "",
  menstruationChoice: "",
};

function localDateValue(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function displayDate(value: string, locale = "th-TH"): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function ScoreMethodDetails() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;

  return (
    <details className="score-method-details">
      <summary>{t("ดูวิธีคำนวณคะแนนและแหล่งอ้างอิง", "Score methods and references")}</summary>
      <div className="score-method-content">
        <section aria-labelledby="predicted-score-method-title">
          <h3 id="predicted-score-method-title">{t("Thirst และ dryness · ผลจากโมเดล", "Thirst and dryness · model estimates")}</h3>
          <p>{t("API ส่งเวลานอนรวม (S), น้ำดื่ม (W) และตัวเลือกเวลาอยู่นอกบ้านเข้า RandomForestRegressor แบบหลายผลลัพธ์ โมเดลเฉลี่ยค่าจากต้นไม้ 300 ต้น แล้วจำกัดคะแนนไว้ 0–10 และปัดทศนิยม 1 ตำแหน่ง", "The API sends total sleep (S), water intake (W), and the outdoor-time choice to a multi-output RandomForestRegressor. It averages 300 decision trees, clips scores to 0–10, and rounds to one decimal place.")}</p>
          <p>{t("โมเดลพื้นฐานใช้ป้ายคะแนนสังเคราะห์จากกฎตัวอย่างเหล่านี้ ไม่ใช่สูตรแพทย์; หากมี candidate ที่ฝึกจากคะแนนที่ผู้ใช้รายงานจริงและได้รับอนุมัติ ระบบจะใช้ candidate นั้นทำนายวันถัดไป พร้อมแสดงวันที่เป้าหมายในผลคะแนน:", "The baseline model uses synthetic labels from the example rules below; these are not medical formulas. Once a candidate trained on user-reported scores is approved, it predicts the next day and shows the target date:")}</p>
          <code>thirst = clip(round(1.5 + max(0, (420 − S) ÷ 80) + max(0, (1500 − W) ÷ 200), 1), 0, 10)</code>
          <code className="dryness-formula">{`skin_dryness_score_0_10 = round(U(min, max), 1)
(min, max) =
  (1, 3)   if S ≥ 420 and W ≥ 1500
  (4, 6)   if S ≥ 420 and W < 1500
  (7, 10)  if S < 360 and W < 1500
  (2, 7)   otherwise`}</code>
          <p>{t("U(min, max) คือการสุ่มค่าแบบ uniform ในช่วงที่ตรงเงื่อนไข แล้วปัดทศนิยม 1 ตำแหน่ง; สูตรนี้ใช้สร้าง target สำหรับฝึก ส่วนโมเดลจริงเรียนรู้ความสัมพันธ์จาก target เหล่านี้แล้วทำนายคะแนน", "U(min, max) is a uniform random value within the matching range, rounded to one decimal place. This creates training targets; the model learns from those targets to estimate scores.")}</p>
          <p>{t("ค่า 420 นาทีและ 1,500 มล. เป็นจุดอ้างอิงในการจำลองชุดข้อมูล ไม่ใช่เกณฑ์ทางการแพทย์ และข้อมูลน้ำในฟอร์มไม่ใช่ total water จากอาหารและเครื่องดื่มทั้งหมด ตัวเลือกเวลาอยู่นอกบ้านเป็น feature ของโมเดล แต่ไม่ได้อยู่ในกฎสร้างป้าย thirst/dryness จึงใช้สรุปเหตุและผลหรือประเมินรังสี UV ไม่ได้", "The 420-minute and 1,500-mL values are synthetic-data reference points, not medical thresholds. The water field does not include all water from food and drinks. Outdoor time is a model feature but is not part of the thirst/dryness label rule, so it cannot establish causation or estimate UV exposure.")}</p>
          <h3>{t("Sleep score · คำนวณจากระยะเวลาเท่านั้น", "Sleep score · duration only")}</h3>
          <code>sleep_score_0_100 = round(min(100, sleep_duration_total_minutes ÷ 540 × 100), 1)</code>
          <p>{t("คะแนนเต็มเมื่อถึงเพดานสูตร 9 ชั่วโมง และยังรับเวลานอนได้ถึง 10 ชั่วโมง; เป็นสเกลของแอป ไม่ใช่คะแนนทางการแพทย์หรือคุณภาพการนอน ส่วนเวลานอนที่แนะนำจะแสดงแยกตามช่วงวัยตามแนวทาง CDC", "The score reaches its formula cap at 9 hours, while sleep input is accepted up to 10 hours. It is an app scale, not a medical or sleep-quality score. General sleep-duration guidance is shown separately by age group using CDC guidance.")}</p>
          <div className="score-method-references" aria-label={t("แหล่งอ้างอิง", "References")}>
            <a href="https://www.cdc.gov/sleep/about/" target="_blank" rel="noreferrer">CDC: {t("ระยะเวลานอนทั่วไปตามช่วงวัย", "recommended sleep duration by age")}</a>
            <a href="https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/reduce-premature-aging-skin" target="_blank" rel="noreferrer">AAD: {t("ลดปัจจัยที่เร่งผิวแก่ก่อนวัย", "reducing premature skin aging")}</a>
            <a href="https://www.aad.org/public/everyday-care/skin-care-basics/dry/dermatologists-tips-relieve-dry-skin" target="_blank" rel="noreferrer">AAD: {t("ดูแลผิวแห้งและเลือกมอยส์เจอไรเซอร์", "dry skin care and moisturizers")}</a>
            <a href="https://www.cdc.gov/tobacco/about/benefits-of-quitting.html" target="_blank" rel="noreferrer">CDC: {t("ประโยชน์ของการเลิกบุหรี่", "benefits of quitting smoking")}</a>
            <a href="https://www.nhs.uk/symptoms/period-pain/" target="_blank" rel="noreferrer">NHS: {t("การดูแลอาการปวดประจำเดือน", "period pain self-care")}</a>
            <a href="https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html" target="_blank" rel="noreferrer">scikit-learn: {t("วิธีทำงานของ RandomForestRegressor", "RandomForestRegressor")}</a>
            <a href="https://nap.nationalacademies.org/read/10925/chapter/2" target="_blank" rel="noreferrer">National Academies: {t("น้ำรวมจากน้ำดื่ม เครื่องดื่ม และอาหาร", "total water from drinking water, beverages, and food")}</a>
            <a href="https://doi.org/10.1111/srt.12454" target="_blank" rel="noreferrer">Akdeniz et al. (2018): {t("ทบทวนหลักฐานเรื่องน้ำกับความชุ่มชื้นผิว", "review of evidence on water intake and skin hydration")}</a>
          </div>
        </section>
      </div>
    </details>
  );
}

export default function DailyHealthTracker({ initialDate }: { initialDate: string }) {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const locale = language === "en" ? "en-US" : "th-TH";
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [today, setToday] = useState(initialDate);
  const [form, setForm] = useState<FormValues>(emptyForm);
  const [entry, setEntry] = useState<DailyEntry | null>(null);
  const [formError, setFormError] = useState("");
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [personalProfile, setPersonalProfile] = useState<DailyHealthProfile>({
    has_session: false,
    consent_active: false,
    age_guidance_consent_active: false,
    model_training_consent_active: false,
    can_report_outcomes: false,
    age_band: null,
    smoking_status: null,
  });
  const [isPredicting, setIsPredicting] = useState(false);
  const [storageStatus, setStorageStatus] = useState<StorageStatus>("idle");
  const [storageMessage, setStorageMessage] = useState("");
  const predictionRequestId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/daily-health/profile", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load personal health settings");
        return (await response.json()) as DailyHealthProfile;
      })
      .then((profile) => {
        setPersonalProfile(profile);
        if (profile.consent_active || profile.age_guidance_consent_active || profile.model_training_consent_active) {
          setForm((current) => ({
            ...current,
            personalizationConsent: profile.consent_active || current.personalizationConsent,
            ageGuidanceConsent: profile.age_guidance_consent_active || current.ageGuidanceConsent,
            modelTrainingConsent: profile.model_training_consent_active,
            ageBand: profile.age_guidance_consent_active ? profile.age_band ?? "" : current.ageBand,
            smokingStatus: profile.consent_active ? profile.smoking_status ?? "" : current.smokingStatus,
          }));
        }
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

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

  async function deletePersonalProfile() {
    if (!window.confirm(t("ลบข้อมูลช่วงวัย สถานะการสูบบุหรี่ และเช็กอินประจำเดือนที่บันทึกไว้หรือไม่?", "Delete the saved age group, smoking status, and menstrual check-ins?"))) return;
    try {
      const response = await fetch("/api/daily-health/profile", {
        method: "DELETE",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(t("ลบข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not delete the information. Please try again."));
      setPersonalProfile({
        has_session: true,
        consent_active: false,
        age_guidance_consent_active: false,
        model_training_consent_active: personalProfile.model_training_consent_active,
        can_report_outcomes: true,
        age_band: null,
        smoking_status: null,
      });
      setForm((current) => ({
        ...current,
        personalizationConsent: false,
        ageGuidanceConsent: false,
        ageBand: "",
        smokingStatus: "",
        menstruationChoice: "",
      }));
      setStorageStatus("saved");
      setStorageMessage(t("ลบข้อมูลส่วนบุคคลและถอน consent แล้ว", "Personal information was deleted and consent withdrawn."));
    } catch (error) {
      setStorageStatus("failed");
      setStorageMessage(error instanceof Error ? error.message : t("ลบข้อมูลไม่สำเร็จ", "Could not delete the information."));
    }
  }

  async function revokeModelTrainingConsent() {
    if (!window.confirm(t("หยุดนำข้อมูลของคุณไปสร้าง candidate รุ่นใหม่หรือไม่? ประวัติจะยังอยู่ และโมเดลที่อนุมัติใช้งานแล้วจะไม่ถูกย้อนลบ", "Stop using your data to build future candidate models? Your history will remain, and approved models will not be rolled back."))) return;
    try {
      const response = await fetch("/api/daily-health/training-consent", {
        method: "DELETE",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(t("ถอนความยินยอมไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not withdraw consent. Please try again."));
      setPersonalProfile((current) => ({ ...current, model_training_consent_active: false }));
      setForm((current) => ({ ...current, modelTrainingConsent: false }));
      setStorageStatus("saved");
      setStorageMessage(t("ถอนความยินยอมแล้ว; candidate ที่ยังไม่อนุมัติจะใช้ไม่ได้ และจะไม่นำข้อมูลไปสร้างรุ่นถัดไป", "Consent withdrawn. Unapproved candidates will be disabled, and your data will not be used for future versions."));
    } catch (error) {
      setStorageStatus("failed");
      setStorageMessage(error instanceof Error ? error.message : t("ถอนความยินยอมไม่สำเร็จ", "Could not withdraw consent."));
    }
  }

  async function deleteDailyHealthData() {
    const confirmed = window.confirm(t(
      "ลบประวัติสุขภาพรายวันและคะแนนที่คุณรายงานเองทั้งหมดหรือไม่? การกระทำนี้ย้อนกลับไม่ได้ และจะลบ candidate model ที่ฝึกจากชุดข้อมูลผู้ใช้ร่วมกัน แล้วกลับไปใช้โมเดลพื้นฐาน",
      "Delete all daily health history and self-reported scores? This cannot be undone. It removes the shared user-trained candidate model and returns to the baseline model.",
    ));
    if (!confirmed) return;
    setStorageStatus("saving");
    setStorageMessage("");
    try {
      const response = await fetch("/api/daily-health/data", {
        method: "DELETE",
        cache: "no-store",
      });
      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(typeof result?.detail === "string" ? result.detail : t("ลบข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not delete the data. Please try again."));
      }
      setEntry(null);
      setPrediction(null);
      setForm({ ...emptyForm, date: localDateValue() });
      setPersonalProfile({
        has_session: true,
        consent_active: false,
        age_guidance_consent_active: false,
        model_training_consent_active: false,
        can_report_outcomes: false,
        age_band: null,
        smoking_status: null,
      });
      setStorageStatus("saved");
      setStorageMessage(t("ลบประวัติสุขภาพและผลที่รายงานเองแล้ว; ล้าง candidate model แล้ว บัญชียังคงเข้าสู่ระบบอยู่", "Health history and self-reported outcomes were deleted, and the candidate model was cleared. You remain signed in."));
    } catch (error) {
      setStorageStatus("failed");
      setStorageMessage(error instanceof Error ? error.message : t("ลบข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not delete the data. Please try again."));
    }
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
                      target_date: predictionResult.prediction_target_date,
                    }
            : null,
          personalization_consent: dailyEntry.personalizationConsent,
          age_guidance_consent: dailyEntry.ageGuidanceConsent,
          age_band: dailyEntry.ageGuidanceConsent ? dailyEntry.ageBand : null,
          smoking_status: dailyEntry.personalizationConsent ? dailyEntry.smokingStatus : null,
          currently_menstruating: dailyEntry.personalizationConsent
            ? dailyEntry.currentlyMenstruating
            : null,
          model_training_consent: dailyEntry.modelTrainingConsent,
        }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(typeof result?.detail === "string" ? result.detail : t("ไม่สามารถบันทึกข้อมูลลงฐานข้อมูลได้", "Could not save the data."));
      }
      setStorageStatus("saved");
      setStorageMessage(t("บันทึกข้อมูลรายวันนี้ลงฐานข้อมูลแล้ว · คะแนนจากโมเดลยังไม่ถือเป็นป้ายกำกับจริงสำหรับ train", "Today's record was saved. Model estimates are not ground-truth training labels."));
      try {
        const profileResponse = await fetch("/api/daily-health/profile", { cache: "no-store" });
        if (profileResponse.ok) {
          setPersonalProfile((await profileResponse.json()) as DailyHealthProfile);
        }
      } catch {
        // The daily entry is already saved; profile refresh is best-effort.
      }
    } catch (error) {
      setStorageStatus("failed");
      setStorageMessage(error instanceof Error ? error.message : t("บันทึกข้อมูลไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not save the data. Please try again."));
    }
  }

  async function submitEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hours = Number(form.sleepHours);
    const minutes = Number(form.sleepMinutes);
    const water = Number(form.waterIntakeMl);

    if (!form.date || !form.sleepHours || !form.sleepMinutes || !form.waterIntakeMl || !form.outdoorChoice) {
      setFormError(t("กรุณากรอกข้อมูลให้ครบทุกช่องก่อนดูสรุป", "Complete every required field before viewing the summary."));
      return;
    }
    if (hours * 60 + minutes > 600) {
      setFormError(t("ระยะเวลานอนสูงสุดที่บันทึกได้คือ 600 นาที (10 ชั่วโมง)", "Maximum sleep duration is 600 minutes (10 hours)."));
      return;
    }
    if (form.date > today) {
      setFormError(t("เลือกวันที่วันนี้หรือวันที่ผ่านมาเท่านั้น", "Choose today or a past date."));
      return;
    }
    if (!form.consentToStore) {
      setFormError(t("กรุณายินยอมให้บันทึกข้อมูลรายวันก่อนส่งข้อมูล", "Consent to storing the daily entry is required before submission."));
      return;
    }

    const dailyEntry = {
      date: form.date,
      sleepHours: hours,
      sleepMinutes: minutes,
      sleepDurationMinutes: hours * 60 + minutes,
      waterIntakeMl: water,
      outdoorChoice: form.outdoorChoice,
      modelTrainingConsent: form.modelTrainingConsent,
      personalizationConsent: form.personalizationConsent,
      ageGuidanceConsent: form.ageGuidanceConsent,
      ageBand: form.ageGuidanceConsent && form.ageBand ? form.ageBand : null,
      smokingStatus: form.personalizationConsent && form.smokingStatus ? form.smokingStatus : null,
      currentlyMenstruating: form.personalizationConsent && form.menstruationChoice
        ? form.menstruationChoice === "yes"
        : null,
    } satisfies DailyEntry;
    const selectedChoice = outdoorOptions.find((option) => option.value === form.outdoorChoice);
    const requestId = ++predictionRequestId.current;
    setEntry(dailyEntry);
    setPrediction(null);
    setIsPredicting(true);
    setStorageStatus("saving");
      setStorageMessage(t("กำลังบันทึกข้อมูลรายวันลงฐานข้อมูล", "Saving today's health record…"));
    setForm((current) => ({ ...current, consentToStore: false, menstruationChoice: "" }));
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
          personal_context: dailyEntry.personalizationConsent || dailyEntry.ageGuidanceConsent
            ? {
                consent_given: dailyEntry.personalizationConsent,
                age_guidance_consent_given: dailyEntry.ageGuidanceConsent,
                age_band: dailyEntry.ageGuidanceConsent ? dailyEntry.ageBand : null,
                smoking_status: dailyEntry.personalizationConsent ? dailyEntry.smokingStatus : null,
                currently_menstruating: dailyEntry.personalizationConsent
                  ? dailyEntry.currentlyMenstruating
                  : null,
              }
            : null,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(typeof result.detail === "string" ? result.detail : t("ไม่สามารถเรียกโมเดลได้", "Could not request a prediction."));
      }
      predictionResult = result as PredictionResponse;
      if (requestId === predictionRequestId.current) setPrediction(predictionResult);
    } catch {
      predictionResult = null;
    }
    await saveEntry(dailyEntry, predictionResult);
    if (requestId === predictionRequestId.current) setIsPredicting(false);
  }

  const selectedOutdoor = outdoorOptions.find((option) => option.value === entry?.outdoorChoice);
  const calculatedSleepScore = entry
    ? prediction?.calculated.sleep_score_0_100
      ?? Number(Math.min(100, (entry.sleepDurationMinutes / 540) * 100).toFixed(1))
    : null;

  return (
    <div className="clients-tracker">
      <section className="daily-entry-card" aria-labelledby="daily-entry-title">
        <div className="daily-entry-copy">
      <p className="eyebrow">{t("บันทึกประจำวัน", "DAILY CHECK-IN")}</p>
          <h2 id="daily-entry-title">{t("ข้อมูลสุขภาพรายวัน", "Daily health entry")}</h2>
          <p>{t("วันที่จะตั้งเป็นวันนี้ให้อัตโนมัติ และสามารถเลือกวันที่ย้อนหลังได้", "The date defaults to today; you can also choose a past date.")}</p>
        </div>
        <button className="primary-button daily-open-button" type="button" onClick={openDialog}>
          {entry ? t("แก้ไขข้อมูลที่กรอก", "Edit today's entry") : t("＋ กรอกข้อมูลรายวัน", "＋ Add daily entry")}
        </button>
      </section>

      <dialog className="daily-entry-dialog" ref={dialogRef} aria-labelledby="daily-dialog-title">
        <button className="close-button" type="button" onClick={closeDialog} aria-label={t("ปิดแบบฟอร์ม", "Close form")}>×</button>
        <p className="eyebrow">DAILY CHECK-IN</p>
        <h2 id="daily-dialog-title">{t("กรอกข้อมูลสุขภาพรายวัน", "Enter your daily health information")}</h2>
        <p className="dialog-description">{t("กรอกค่าที่คุณสังเกตหรือบันทึกได้ ข้อมูลนี้ไม่ใช่ผลวินิจฉัย", "Enter what you observed or recorded. This is not a diagnosis.")}</p>

        <form className="daily-entry-form" onSubmit={submitEntry}>
          <label className="tracker-field" htmlFor="entry-date">
            <span>{t("วันที่", "Date")}</span>
            <input
              id="entry-date"
              type="date"
              value={form.date}
              max={today || undefined}
              required
              onChange={(event) => updateForm("date", event.target.value)}
            />
            <small>{t("ค่าเริ่มต้นคือวันที่ปัจจุบันของอุปกรณ์", "Defaults to your device's current date.")}</small>
          </label>

          <fieldset className="tracker-field sleep-field">
            <legend>{t("ระยะเวลาการนอน", "Sleep duration")}</legend>
            <div className="sleep-inputs">
              <label htmlFor="sleep-hours"><span>{t("ชั่วโมง", "Hours")}</span><input id="sleep-hours" type="number" min="0" max="10" step="1" inputMode="numeric" placeholder={t("เช่น 7", "e.g. 7")} required value={form.sleepHours} onChange={(event) => updateForm("sleepHours", event.target.value)} /></label>
              <label htmlFor="sleep-minutes"><span>{t("นาที", "Minutes")}</span><input id="sleep-minutes" type="number" min="0" max="59" step="1" inputMode="numeric" placeholder={t("เช่น 30", "e.g. 30")} required value={form.sleepMinutes} onChange={(event) => updateForm("sleepMinutes", event.target.value)} /></label>
            </div>
            <small>{t("รับได้สูงสุด 10 ชั่วโมง; คะแนนเวลานอนเต็มที่เมื่อถึงเพดานสูตร 9 ชั่วโมง", "Input is capped at 10 hours; the sleep score reaches its cap at 9 hours.")}</small>
          </fieldset>

          <label className="tracker-field" htmlFor="water-intake">
            <span>{t("ปริมาณน้ำดื่ม (มล.)", "Water intake (mL)")}</span>
            <input id="water-intake" type="number" min="0" max="20000" step="1" inputMode="numeric" placeholder={t("เช่น 1500", "e.g. 1500")} required value={form.waterIntakeMl} onChange={(event) => updateForm("waterIntakeMl", event.target.value)} />
            <small>{t("กรอกยอดสะสมทั้งวัน; โมเดลฝึกด้วยช่วง 900–1,800 มล. ถ้ากรอกยอดระหว่างวันอาจอยู่นอกช่วงฝึก", "Enter your full-day total. The model was trained on 900–1,800 mL, so an in-progress value may be outside its training range.")}</small>
          </label>

          <fieldset className="tracker-field outdoor-field">
            <legend>{t("เวลาอยู่นอกบ้าน", "Time outdoors")}</legend>
            <div className="outdoor-options">
              {outdoorOptions.map((option, index) => (
                <label className={`outdoor-choice${form.outdoorChoice === option.value ? " selected" : ""}`} key={option.value}>
                  <input type="radio" name="outdoor-choice" value={option.value} checked={form.outdoorChoice === option.value} required onChange={() => updateForm("outdoorChoice", option.value)} />
                  <span className="outdoor-choice-number">{index + 1}</span>
                  <span className="outdoor-choice-text"><strong>{t(option.label, ["Under 1 hour", "1 to under 3 hours", "3 to under 4 hours", "4 hours or more"][index])}</strong><small>{t(option.range, ["0 to under 60 minutes", "60 to under 180 minutes", "180 to under 240 minutes", "240 minutes or more"][index])}</small></span>
                </label>
              ))}
            </div>
            <small className="range-note">{t("กำหนดเส้นแบ่งให้ไม่ซ้อนกัน: ตัวเลือก 2 ครอบคลุม 1 ถึงน้อยกว่า 3 ชั่วโมง และตัวเลือก 4 เริ่มตั้งแต่ 4 ชั่วโมง", "Ranges do not overlap: choice 2 covers 1 to under 3 hours, and choice 4 starts at 4 hours.")}</small>
          </fieldset>

          <fieldset className="personal-context-fieldset">
            <legend>{t("ข้อมูลส่วนบุคคลเพื่อปรับคำแนะนำ (ไม่บังคับ)", "Optional personal context for guidance")}</legend>
            <label className="personalization-consent">
              <input
                type="checkbox"
                checked={form.personalizationConsent}
                onChange={(event) => updateForm("personalizationConsent", event.target.checked)}
              />
              <span>{t("ยินยอมให้ใช้และบันทึกสถานะสูบบุหรี่และเช็กอินประจำเดือน เพื่อปรับคำแนะนำเท่านั้น ไม่ใช้วินิจฉัยโรค", "I consent to using and saving smoking status and menstrual check-ins for personalized guidance only, not diagnosis.")}</span>
            </label>
            {form.personalizationConsent && (
              <div className="personal-context-fields">
                <label className="tracker-field" htmlFor="smoking-status">
                  <span>{t("สถานะการสูบบุหรี่", "Smoking status")}</span>
                  <select
                    id="smoking-status"
                    value={form.smokingStatus}
                    onChange={(event) => updateForm("smokingStatus", event.target.value as SmokingStatus | "")}
                  >
                    <option value="">
                      {personalProfile.smoking_status ? t("ใช้สถานะเดิมที่บันทึกไว้", "Use saved status") : t("ยังไม่ระบุ", "Not specified")}
                    </option>
                    <option value="current">{t("ปัจจุบันสูบบุหรี่", "Currently smoke")}</option>
                    <option value="former">{t("เคยสูบ แต่เลิกแล้ว", "Former smoker")}</option>
                    <option value="never">{t("ไม่เคยสูบ", "Never smoked")}</option>
                    <option value="prefer_not_to_say">{t("ไม่ต้องการระบุ", "Prefer not to say")}</option>
                  </select>
                </label>
                <fieldset className="tracker-field">
                  <legend>{t("กำลังมีประจำเดือนวันนี้หรือไม่ (ไม่บังคับ)", "Are you menstruating today? (Optional)")}</legend>
                  <div className="period-checkin-options">
                    <label>
                      <input
                        type="radio"
                        name="period-checkin"
                        checked={form.menstruationChoice === ""}
                        onChange={() => updateForm("menstruationChoice", "")}
                      />
                      <span>{t("ไม่แชร์วันนี้", "Skip today")}</span>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="period-checkin"
                        checked={form.menstruationChoice === "yes"}
                        onChange={() => updateForm("menstruationChoice", "yes")}
                      />
                      <span>{t("ใช่", "Yes")}</span>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="period-checkin"
                        checked={form.menstruationChoice === "no"}
                        onChange={() => updateForm("menstruationChoice", "no")}
                      />
                      <span>{t("ไม่ใช่", "No")}</span>
                    </label>
                  </div>
                </fieldset>
              </div>
            )}
            <label className="personalization-consent">
              <input
                type="checkbox"
                checked={form.ageGuidanceConsent}
                onChange={(event) => updateForm("ageGuidanceConsent", event.target.checked)}
              />
              <span>{t("ยินยอมแยกต่างหากให้บันทึกช่วงวัยเพื่อแสดงแนวทางเวลานอนทั่วไปตามวัย (ไม่เก็บวันเกิด)", "I separately consent to saving my age group for general age-based sleep guidance. Date of birth is not collected.")}</span>
            </label>
            {form.ageGuidanceConsent && (
              <label className="tracker-field" htmlFor="age-band">
                <span>{t("ช่วงวัยสำหรับคำแนะนำการนอน", "Age group for sleep guidance")}</span>
                <select
                  id="age-band"
                  value={form.ageBand}
                  onChange={(event) => updateForm("ageBand", event.target.value as AgeBand | "")}
                >
                  <option value="">{personalProfile.age_band ? t("ใช้ช่วงวัยเดิมที่บันทึกไว้", "Use saved age group") : t("เลือกช่วงวัย", "Choose an age group")}</option>
                  <option value="13_17">{t("13–17 ปี", "13–17 years")}</option>
                  <option value="18_60">{t("18–60 ปี", "18–60 years")}</option>
                  <option value="61_64">{t("61–64 ปี", "61–64 years")}</option>
                  <option value="65_plus">{t("65 ปีขึ้นไป", "65 years and older")}</option>
                </select>
                <small>{t("เก็บเฉพาะช่วงอายุ ไม่เก็บวันเกิด; หากไม่เลือกจะใช้คำแนะนำทั่วไป", "Only the age group is saved, not date of birth. General guidance is used when not selected.")}</small>
              </label>
            )}
            <small>
              {t("ข้อมูลที่เคยบันทึกจะคงอยู่จนกดถอน consent และลบข้อมูลด้านล่าง; เช็กอินประจำเดือนเลือกแชร์แยกในแต่ละวัน", "Saved information remains until you withdraw consent and delete it below. Menstrual check-ins are optional each day.")}
            </small>
            {(personalProfile.consent_active || personalProfile.age_guidance_consent_active) && (
              <button className="profile-delete-button" type="button" onClick={() => void deletePersonalProfile()}>
                {t("ถอน consent และลบข้อมูลส่วนบุคคลที่บันทึกไว้", "Withdraw consent and delete saved personal data")}
              </button>
            )}
          </fieldset>

          <label className="daily-data-consent">
            <input type="checkbox" required checked={form.consentToStore} onChange={(event) => updateForm("consentToStore", event.target.checked)} />
            <span>{t("ยินยอมให้บันทึกข้อมูลสุขภาพรายวันนี้ในฐานข้อมูลเพื่อใช้กับประวัติและพัฒนาระบบต่อ โดยเข้าใจว่าคะแนนจากโมเดลเป็นเพียงค่าคาดการณ์ ไม่ใช่คะแนนจริงสำหรับใช้ train", "I consent to saving today's health entry for history and system improvement. I understand model estimates are predictions, not ground-truth training labels.")}</span>
          </label>

          {!personalProfile.model_training_consent_active ? (
            <label className="daily-data-consent model-training-consent">
              <input
                type="checkbox"
                checked={form.modelTrainingConsent}
                onChange={(event) => updateForm("modelTrainingConsent", event.target.checked)}
              />
              <span>
                {t("ยินยอมแยกต่างหากให้นำข้อมูลรายวันที่บันทึกและผล thirst/dryness ที่ฉันรายงานจริงไปใช้ฝึกและประเมิน candidate model รุ่นใหม่; ไม่ใช้คะแนน prediction หรือข้อมูลสังเคราะห์เป็นคำตอบจริง", "I separately consent to using my saved daily data and self-reported thirst/dryness outcomes to train and evaluate future candidate models. Predictions and synthetic data are not treated as ground truth.")}
              </span>
            </label>
          ) : (
            <div className="model-training-consent-status">
              <p>{t("คุณยินยอมให้นำข้อมูลรายวันและผลที่รายงานจริงไปสร้าง candidate model แล้ว", "You have consented to using daily data and real reported outcomes for candidate models.")}</p>
              <button className="profile-delete-button" type="button" onClick={() => void revokeModelTrainingConsent()}>
                {t("ถอนความยินยอมสำหรับการฝึกโมเดล", "Withdraw model-training consent")}
              </button>
              <small>{t("การถอนจะหยุดใช้ข้อมูลในรุ่นถัดไป; ไม่ได้ลบประวัติหรือย้อนลบรุ่นโมเดลที่สร้างเสร็จแล้ว", "Withdrawal stops use in future versions; it does not delete history or roll back completed models.")}</small>
            </div>
          )}

          {formError && <p className="tracker-form-error" role="alert">{formError}</p>}
          <div className="tracker-form-actions">
            <button className="secondary-button" type="button" onClick={closeDialog}>{t("ยกเลิก", "Cancel")}</button>
            <button className="primary-button" type="submit">{t("บันทึกและแสดงผล", "Save and view results")}</button>
          </div>
        </form>
      </dialog>

      <section className="tracker-results" aria-labelledby="tracker-results-title">
        <div className="tracker-section-heading">
          <div>
            <p className="eyebrow">{t("ผลประจำวัน", "DAILY RESULT")}</p>
            <h2 id="tracker-results-title">{t("ผลวันนี้", "Today's result")}</h2>
          </div>
        </div>

        {entry ? (
          <>
            <p className="entry-date-line" role="status" aria-live="polite">{t("สรุปข้อมูลวันที่", "Summary for")} {displayDate(entry.date, locale)}</p>
            <div className="tracker-metric-grid">
              <article className="tracker-metric duration-metric">
                <p className="eyebrow">{t("ระยะเวลานอนที่คำนวณได้", "SLEEP DURATION")}</p>
                <strong>{entry.sleepHours} {t("ชม.", "hr")} {entry.sleepMinutes} {t("นาที", "min")}</strong>
                <p>{t("รวม", "Total")} {entry.sleepDurationMinutes.toLocaleString(locale)} {t("นาที", "minutes")}</p>
              </article>
              <article className="tracker-metric sleep-score-metric">
                <p className="eyebrow">SLEEP SCORE</p>
                <strong>{calculatedSleepScore?.toFixed(1) ?? "—"} <small>/ 100</small></strong>
                <p>{t("คะแนนเต็มที่เพดานสูตร 9 ชั่วโมง", "Score caps at the 9-hour formula limit.")}</p>
              </article>
              <article className="tracker-metric pending-metric">
                <p className="eyebrow">THIRST SCORE</p>
                <strong>{isPredicting ? "…" : prediction?.predictions.thirst_score_0_10.value?.toFixed(1) ?? "—"} <small>/ 10</small></strong>
                <p>{prediction?.predictions.thirst_score_0_10.value == null ? t("ไม่มีคะแนนในรอบนี้", "No score available this time") : prediction.model?.prediction_horizon_days ? `${t("คาดการณ์สำหรับ", "Forecast for")} ${displayDate(prediction.prediction_target_date, locale)}` : t("ค่าประเมินจากข้อมูลวันนี้", "Estimate from today's data")}</p>
              </article>
              <article className="tracker-metric pending-metric">
                <p className="eyebrow">DRYNESS SCORE</p>
                <strong>{isPredicting ? "…" : prediction?.predictions.skin_dryness_score_0_10.value?.toFixed(1) ?? "—"} <small>/ 10</small></strong>
                <p>{prediction?.predictions.skin_dryness_score_0_10.value == null ? t("ไม่มีคะแนนในรอบนี้", "No score available this time") : prediction.model?.prediction_horizon_days ? `${t("คาดการณ์สำหรับ", "Forecast for")} ${displayDate(prediction.prediction_target_date, locale)}` : t("ค่าประเมินจากข้อมูลวันนี้", "Estimate from today's data")}</p>
              </article>
            </div>
            <div className="entry-summary" aria-label={t("ข้อมูลที่กรอก", "Entered data")}>
              <span>{t("น้ำดื่ม", "Water intake")} <strong>{entry.waterIntakeMl.toLocaleString(locale)} {t("มล.", "mL")}</strong></span>
              <span>{t("เวลาอยู่นอกบ้าน", "Time outdoors")} <strong>{selectedOutdoor ? t(selectedOutdoor.label, ["Under 1 hour", "1 to under 3 hours", "3 to under 4 hours", "4 hours or more"][outdoorOptions.indexOf(selectedOutdoor)]) : "—"}</strong></span>
            </div>
            <p className={`storage-status storage-status-${storageStatus}`} role="status" aria-live="polite">
              {storageMessage || (storageStatus === "saved" ? t("บันทึกข้อมูลรายวันนี้ลงฐานข้อมูลแล้ว", "Today's record was saved.") : "")}
            </p>
            {storageStatus === "failed" && (
              <button className="secondary-button storage-retry" type="button" onClick={() => void saveEntry(entry, prediction)}>
                {t("ลองบันทึกอีกครั้ง", "Try saving again")}
              </button>
            )}
          </>
        ) : (
          <div className="tracker-empty-state">
            <span className="tracker-empty-icon" aria-hidden="true">＋</span>
            <h3>{t("เริ่มจากบันทึกข้อมูลของวันนี้", "Start by recording today's information")}</h3>
            <p>{t("บันทึกการนอน น้ำดื่ม และเวลาอยู่นอกบ้านเพื่อดูคะแนนและคำแนะนำสำหรับวันนี้", "Log sleep, water intake and time outdoors to see today's estimates and guidance.")}</p>
          </div>
        )}

        {!entry && storageMessage && (
          <p
            className={`storage-status storage-status-${storageStatus}`}
            role="status"
            aria-live="polite"
          >
            {storageMessage}
          </p>
        )}

        {prediction && <DailyHealthDashboard prediction={prediction} />}
        <ScoreMethodDetails />
      </section>

      {personalProfile.has_session && (
        <section className="daily-data-delete-panel" aria-labelledby="daily-data-delete-title">
          <div>
            <h2 id="daily-data-delete-title">{t("จัดการข้อมูลสุขภาพ", "Manage health data")}</h2>
            <p>{t("ลบข้อมูลรายวันและผลที่รายงานเองของบัญชีนี้ได้ทุกเมื่อ การลบจะทำให้ candidate model ที่ฝึกจากข้อมูลผู้ใช้ทั้งหมดใช้ต่อไม่ได้ และระบบกลับไปใช้โมเดลพื้นฐาน", "You can delete this account's daily entries and self-reported outcomes at any time. Deleting them invalidates the shared user-trained candidate and returns the system to its baseline model.")}</p>
          </div>
          <button className="profile-delete-button" type="button" onClick={() => void deleteDailyHealthData()}>
            {t("ลบข้อมูลสุขภาพรายวันทั้งหมด", "Delete all daily health data")}
          </button>
        </section>
      )}

      {personalProfile.can_report_outcomes && (
        <DailyHealthOutcomeForm initialDate={initialDate} />
      )}
    </div>
  );
}
