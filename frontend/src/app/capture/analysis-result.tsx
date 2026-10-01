"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Eye,
  Info,
  Layers,
  Lock,
  Maximize2,
  ShieldCheck,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { RecommendationPanel } from "@/app/recommendation/recommendation-panel";
import "../result-detail/result-detail.css";
import { useLanguage, type Language } from "@/components/language-provider";

type AreaScore = { score: number; wrinkle_area_ratio: number; wrinkle_pixels: number; evaluated_pixels: number };
type Score = { overall: AreaScore; regions: Record<string, AreaScore>; formula: string; disclaimer: string };
type Result = {
  status: string;
  derived_score?: Score | null;
  experimental_score?: Score | null;
  artifacts_expires_at?: string;
  recommendation_gate?: { eligible: boolean; reasons: string[] };
};
type Analysis = {
  id: string;
  status: "queued" | "running" | "completed" | "rejected" | "failed";
  quality_flags: string[];
  error_category: string | null;
  created_at?: string;
  result: Result | null;
};
type ArtifactAvailability = "available" | "expired" | "unavailable" | "load-error";

const PAGE_COPY = {
  th: {
    pageTitle: "ผลวิเคราะห์ใบหน้า",
    resultTitle: "ผลจากภาพที่ส่งวิเคราะห์",
    resultIntro: "แสดงค่าที่ระบบประเมินได้จากภาพนี้เท่านั้น",
    retryAnalysis: "วิเคราะห์ภาพใหม่",
    backHome: "กลับหน้าภาพรวม",
    actions: "การดำเนินการกับผลวิเคราะห์",
    noAnalysis: "ยังไม่มีผลวิเคราะห์ในเบราว์เซอร์นี้",
    noAnalysisBody: "ส่งภาพใบหน้าที่หน้า “วิเคราะห์” เมื่อประมวลผลเสร็จ ผลจริงจะแสดงที่หน้านี้",
    loadErrorTitle: "โหลดผลวิเคราะห์ไม่สำเร็จ",
    loadError: "ไม่สามารถโหลดผลวิเคราะห์ได้ในขณะนี้ กรุณาลองอีกครั้ง",
    retryLoad: "ลองโหลดอีกครั้ง",
    loading: "กำลังโหลดผลวิเคราะห์…",
    processing: "กำลังประมวลผลภาพ กรุณารอสักครู่…",
    rejectedTitle: "ภาพไม่ผ่านการตรวจคุณภาพ",
    rejectedBody: "กรุณาลองถ่ายภาพใหม่ โดยจัดใบหน้าให้ชัดและหันตรงเข้าหากล้อง",
    chooseImage: "เลือกภาพใหม่",
    failedTitle: "ประมวลผลไม่สำเร็จ",
    failedBody: "กรุณาลองอีกครั้งด้วยภาพใหม่",
    tryAgain: "ลองใหม่",
    imageHeading: "ภาพผลวิเคราะห์",
    imageSubheading: "คลิกที่ภาพเพื่อขยายดูเส้นริ้วรอยที่ตรวจพบ",
    artifactControls: "เลือกรูปแบบภาพผลวิเคราะห์",
    overlay: "ภาพซ้อนตำแหน่ง",
    mask: "เฉพาะพื้นที่ตรวจพบ",
    overlayAlt: "ภาพใบหน้าพร้อมบริเวณที่โมเดลทำเครื่องหมาย",
    maskAlt: "ภาพแสดงเฉพาะบริเวณที่โมเดลทำเครื่องหมาย",
    expired: "ภาพผลวิเคราะห์หมดอายุแล้ว กรุณาวิเคราะห์ภาพใหม่เพื่อดูภาพประกอบ",
    unavailable: "ไม่มีภาพผลวิเคราะห์ที่เปิดดูได้ กรุณาวิเคราะห์ภาพใหม่",
    imageLoadError: "โหลดภาพผลวิเคราะห์ไม่สำเร็จ กรุณาลองอีกครั้งหรือวิเคราะห์ภาพใหม่",
    overlayCaption: "สีบนภาพแสดงบริเวณที่โมเดลทำเครื่องหมาย",
    expiryPrefix: "ภาพส่วนตัวเปิดดูได้ถึง",
    thailandTime: "เวลาไทย",
    artifactExpired: "ภาพหมดอายุการเข้าถึงแล้ว",
    markedArea: "พื้นที่ที่ตรวจพบ",
    markedAreaExplanation: "เปอร์เซ็นต์คือสัดส่วนพิกเซลที่โมเดลทำเครื่องหมายจากพื้นที่ใบหน้าที่ประเมินได้ ไม่ใช่คะแนนผิวหรือการวินิจฉัยทางการแพทย์",
    experimentalScore: "คะแนนเชิงทดลอง",
    scoreExplanation: "คะแนน 0–100 คำนวณจากสัดส่วนพื้นที่ที่ทำเครื่องหมายและมีเพดานที่ 100 คะแนนสูงขึ้นหมายถึงสัดส่วนตามสูตรสูงขึ้น ไม่ได้บอกว่าผิวดีขึ้นหรือแย่ลง",
    scoreExplanationBrief: "คำนวณจากสัดส่วนพื้นที่พิกเซล (เพดาน 100)",
    regionsHeading: "การกระจายตัวตามบริเวณใบหน้า",
    regionsScored: "บริเวณที่มีคะแนน",
    regionExplanation: "แสดงสัดส่วนพื้นที่และคะแนนที่ตรวจพบในแต่ละบริเวณสำคัญของใบหน้า",
    unscorable: "ประเมินไม่ได้",
    noRegionPixels: "ไม่มีพิกเซลเพียงพอสำหรับคำนวณ",
    area: "พื้นที่ที่ทำเครื่องหมาย",
    percentageOfEvaluatedArea: "ของพื้นที่ที่ประเมินได้",
    viewAllRegionsAndPixels: "ดูข้อมูลพิกเซลและสูตรคำนวณ",
    viewPixelCounts: "ดูข้อมูลพิกเซลและสูตรคำนวณ",
    pixelCounts: "พิกเซลที่ทำเครื่องหมาย / ที่ประเมินได้",
    pixels: "พิกเซล",
    recommendations: "ผลิตภัณฑ์และคำแนะนำสำหรับคุณ",
    recommendationsEyebrow: "ขั้นตอนถัดไปสำหรับการดูแลผิว",
    recommendationsDesc: "คำแนะนำและผลิตภัณฑ์ที่คัดสรรให้สอดคล้องกับตำแหน่งริ้วรอยที่ตรวจพบและสภาพผิวของคุณ",
    method: "วิธีคำนวณและสูตรคะแนน",
    ratioFormula: "สัดส่วนพื้นที่ที่ทำเครื่องหมาย = พิกเซลที่ทำเครื่องหมาย ÷ พิกเซลที่ประเมินได้",
    scoreFormula: "สูตรคะแนน 0–100:",
    decimalNote: "ใช้สัดส่วนแบบทศนิยม (1% = 0.01)",
    thisImage: "ภาพนี้:",
    scoreCapped: "คะแนนมีเพดานที่ 100 จึงควรดูเปอร์เซ็นต์พื้นที่จริงประกอบ คะแนนนี้ไม่ยืนยันว่ามีหรือไม่มีริ้วรอยจริง",
    disclaimerTitle: "ข้อควรรู้และการปฏิเสธความรับผิดชอบ",
    disclaimer: "ผลนี้เป็นการวัดเชิงทดลองจากภาพถ่าย ไม่ใช่การวินิจฉัยหรือการประเมินสุขภาพผิว และยังไม่ได้รับการรับรองทางคลินิก",
    noScore: "ไม่มีคะแนนสำหรับภาพนี้",
    queued: "รอประมวลผล",
    running: "กำลังประมวลผล",
    analyzed: "วิเคราะห์เมื่อ",
    regionsSummary: (scored: number, total: number) => `${scored} จาก ${total} บริเวณมีคะแนน`,
    analysisEyebrow: "การวิเคราะห์ภาพถ่ายใบหน้าด้วย AI",
    qualityVerified: "ผ่านเกณฑ์คุณภาพภาพถ่าย",
    privacyBadge: "ลบภาพอัตโนมัติภายใน 24 ชม.",
    zoom: "ขยายดูภาพ",
    zoomIn: "ขยาย",
    zoomOut: "ย่อ",
    zoomReset: "ขนาดปกติ",
    closeZoom: "ปิดภาพขยาย",
    clickToZoom: "คลิกเพื่อขยายดูภาพ",
    legendWrinkles: "เส้นสี: บริเวณริ้วรอยที่ตรวจพบ",
    legendEvaluated: "กรอบสว่าง: ขอบเขตใบหน้าที่ประเมิน",
    legendTitle: "คำอธิบายภาพ",
    viewTechnicalData: "ดูข้อมูลพิกเซลและสูตรคำนวณ",
    levelLow: "ตรวจพบน้อย",
    levelModerate: "ตรวจพบปานกลาง",
    levelElevated: "ตรวจพบชัดเจน",
    summaryCardTitle: "สรุปผลการประเมินภาพรวม",
  },
  en: {
    pageTitle: "Face analysis results",
    resultTitle: "Results from this image",
    resultIntro: "Only measurements returned for this image are shown.",
    retryAnalysis: "Analyze a new image",
    backHome: "Back to overview",
    actions: "Face analysis actions",
    noAnalysis: "No analysis is available in this browser",
    noAnalysisBody: "Submit a face image from Analyze. Its result will appear here when processing is complete.",
    loadErrorTitle: "Could not load analysis",
    loadError: "The analysis result could not be loaded. Please try again.",
    retryLoad: "Try loading again",
    loading: "Loading analysis…",
    processing: "Your image is being processed. Please wait…",
    rejectedTitle: "Image did not pass quality checks",
    rejectedBody: "Try a new image with one clear face looking directly at the camera.",
    chooseImage: "Choose a new image",
    failedTitle: "Analysis could not be completed",
    failedBody: "Please try again with a new image.",
    tryAgain: "Try again",
    imageHeading: "Analysis image",
    imageSubheading: "Click image to inspect detected wrinkle lines",
    artifactControls: "Choose an analysis image view",
    overlay: "Marked areas",
    mask: "Mask only",
    overlayAlt: "Face image with the areas marked by the model",
    maskAlt: "Image showing only the areas marked by the model",
    expired: "This analysis image has expired. Analyze a new image to view an artifact.",
    unavailable: "No analysis image is available to view. Analyze a new image.",
    imageLoadError: "Could not load this analysis image. Try again or analyze a new image.",
    overlayCaption: "Color shows the areas marked by the model.",
    expiryPrefix: "Private image available until",
    thailandTime: "Thailand time",
    artifactExpired: "Image access has expired.",
    markedArea: "Detected Area",
    markedAreaExplanation: "This percentage is the share of evaluated face pixels marked by the model. It is not a skin grade or diagnosis.",
    experimentalScore: "Experimental score",
    scoreExplanation: "The 0–100 score is calculated from marked-area proportion and capped at 100. A higher score means a higher proportion under this formula, not better or worse skin.",
    scoreExplanationBrief: "Calculated from pixel area proportion (capped at 100)",
    regionsHeading: "Facial Regions Breakdown",
    regionsScored: "regions scored",
    regionExplanation: "Shows the proportion of evaluated pixels and score across key facial zones.",
    unscorable: "Not scored",
    noRegionPixels: "There are not enough evaluated pixels to calculate a value.",
    area: "Marked area",
    percentageOfEvaluatedArea: "of evaluated area",
    viewAllRegionsAndPixels: "View pixel counts & formula",
    viewPixelCounts: "View pixel counts & formula",
    pixelCounts: "Pixels marked / evaluated",
    pixels: "pixels",
    recommendations: "Products and guidance for you",
    recommendationsEyebrow: "Next Steps For Skin Care",
    recommendationsDesc: "Guidance and products matched to your detected wrinkle areas and skin profile.",
    method: "Calculation methodology & formula",
    ratioFormula: "Marked-area proportion = marked pixels ÷ evaluated pixels",
    scoreFormula: "0–100 score formula:",
    decimalNote: "The proportion uses decimal form (1% = 0.01).",
    thisImage: "This image:",
    scoreCapped: "The score is capped at 100, so refer to the area percentage as well. It does not confirm whether wrinkles are or are not present.",
    disclaimerTitle: "Important note & disclaimer",
    disclaimer: "This is an experimental image measurement, not a diagnosis or skin-health assessment. It has not been clinically validated.",
    noScore: "No score is available for this image.",
    queued: "Queued for processing",
    running: "Processing",
    analyzed: "Analyzed",
    regionsSummary: (scored: number, total: number) => `${scored} of ${total} regions scored`,
    analysisEyebrow: "AI-Powered Vision Analysis",
    qualityVerified: "Image quality passed",
    privacyBadge: "Auto-deleted within 24h",
    zoom: "Zoom image",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    zoomReset: "Reset",
    closeZoom: "Close zoom",
    clickToZoom: "Click to inspect in detail",
    legendWrinkles: "Colored lines: Detected wrinkle areas",
    legendEvaluated: "Bright area: Evaluated face region",
    legendTitle: "Image legend",
    viewTechnicalData: "View pixel counts & formula",
    levelLow: "Low detection",
    levelModerate: "Moderate detection",
    levelElevated: "Prominent detection",
    summaryCardTitle: "Overall Assessment Summary",
  },
} as const;

const REGIONS: Record<string, { th: string; en: string; tagTh: string; tagEn: string }> = {
  forehead: { th: "หน้าผาก", en: "Forehead", tagTh: "ส่วนบน", tagEn: "Upper" },
  glabella: { th: "ระหว่างคิ้ว", en: "Glabella", tagTh: "หว่างคิ้ว", tagEn: "Brow" },
  image_left_periocular: { th: "รอบดวงตาซ้ายของภาพ", en: "Image-left eye area", tagTh: "รอบตา", tagEn: "Periocular" },
  image_right_periocular: { th: "รอบดวงตาขวาของภาพ", en: "Image-right eye area", tagTh: "รอบตา", tagEn: "Periocular" },
  image_left_cheek: { th: "แก้มซ้ายของภาพ", en: "Image-left cheek", tagTh: "แก้ม", tagEn: "Cheek" },
  image_right_cheek: { th: "แก้มขวาของภาพ", en: "Image-right cheek", tagTh: "แก้ม", tagEn: "Cheek" },
  nasolabial: { th: "ร่องแก้ม", en: "Nasolabial fold", tagTh: "ร่องแก้ม", tagEn: "Mid face" },
  perioral: { th: "รอบปาก", en: "Perioral area", tagTh: "รอบปาก", tagEn: "Lower face" },
};

const QUALITY_FLAG_COPY: Record<string, { th: string; en: string }> = {
  unreadable_image: { th: "ระบบเปิดอ่านไฟล์ภาพนี้ไม่ได้", en: "The image file could not be read." },
  resolution_too_low: { th: "ภาพมีความละเอียดไม่เพียงพอสำหรับการประเมิน", en: "The image resolution is too low for assessment." },
  no_face_detected: { th: "ระบบหาใบหน้าในภาพไม่พบ", en: "No face was detected in the image." },
  multiple_faces_detected: { th: "พบหลายใบหน้า กรุณาใช้ภาพที่มีใบหน้าคนเดียว", en: "More than one face was detected. Use an image with one face." },
  face_too_small_pixels: { th: "ใบหน้าอยู่ไกลหรือมีขนาดเล็กเกินไปในภาพ", en: "The face is too small or too far away." },
  face_too_small_ratio: { th: "กรุณาถ่ายให้ใบหน้าอยู่ใกล้และมีขนาดใหญ่ขึ้นในภาพ", en: "Move closer so the face takes up more of the image." },
  landmark_confidence_too_low: { th: "ระบบระบุตำแหน่งใบหน้าได้ไม่ชัดเจน", en: "Facial landmarks could not be located confidently." },
  exposure_too_dark: { th: "ภาพมืดเกินไป กรุณาถ่ายในบริเวณที่มีแสงเพียงพอ", en: "The image is too dark. Try a well-lit area." },
  exposure_too_bright: { th: "ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงจ้าที่ใบหน้า", en: "The image is overexposed. Avoid harsh light on the face." },
  dark_clipping_excessive: { th: "รายละเอียดในภาพมืดเกินกว่าจะประเมินได้", en: "Too much image detail is lost in shadow." },
  bright_clipping_excessive: { th: "แสงจ้าทำให้รายละเอียดใบหน้าบางส่วนหายไป", en: "Harsh light obscures some facial detail." },
  image_too_blurry: { th: "ภาพไม่คมชัด กรุณาถือกล้องให้นิ่งแล้วถ่ายใหม่", en: "The image is blurry. Hold the camera steady and try again." },
  pose_roll_excessive: { th: "กรุณาจัดศีรษะให้ตรงกับกล้อง", en: "Keep your head level with the camera." },
  pose_yaw_excessive: { th: "กรุณาหันหน้าเข้าหากล้องโดยตรง", en: "Face the camera directly." },
  pose_pitch_excessive: { th: "กรุณามองตรงและจัดกล้องให้อยู่ระดับใบหน้า", en: "Look forward and hold the camera at face level." },
  invalid_face_bounds: { th: "ระบบระบุขอบเขตใบหน้าได้ไม่ครบถ้วน", en: "The full face boundary could not be identified." },
  face_parsing_area_too_small: { th: "พื้นที่ใบหน้าที่ระบบระบุมีขนาดเล็กเกินไป", en: "The detected face area is too small." },
  face_parsing_area_too_large: { th: "ระบบแยกพื้นที่ใบหน้าออกจากภาพได้ไม่ชัดเจน", en: "The face area could not be separated clearly from the image." },
};

function getArtifactAvailability(expiresAt?: string, expiryTick = 0): ArtifactAvailability {
  if (!expiresAt) return "unavailable";
  const expiration = Date.parse(expiresAt);
  if (!Number.isFinite(expiration)) return "unavailable";
  return expiration <= Date.now() || expiryTick >= expiration ? "expired" : "available";
}

function formatArtifactExpiry(expiresAt: string, language: Language): string | null {
  const timestamp = Date.parse(expiresAt);
  if (!Number.isFinite(timestamp)) return null;
  return new Intl.DateTimeFormat(language === "th" ? "th-TH" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(timestamp);
}

function formatAnalysisDate(createdAt: string | undefined, language: Language): string | null {
  if (!createdAt) return null;
  const timestamp = Date.parse(createdAt);
  if (!Number.isFinite(timestamp)) return null;
  return new Intl.DateTimeFormat(language === "th" ? "th-TH" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(timestamp);
}

function analysisDetail(analysis: Analysis | null, language: Language): string | undefined {
  if (!analysis) return undefined;
  const copy = PAGE_COPY[language];
  const date = formatAnalysisDate(analysis.created_at, language);
  if (analysis.status === "queued" || analysis.status === "running") {
    return [analysis.status === "queued" ? copy.queued : copy.running, date].filter(Boolean).join(" · ");
  }
  return date ? `${copy.analyzed} ${date}` : undefined;
}

function regionLabel(name: string, language: Language): string {
  return REGIONS[name]?.[language] ?? name;
}

function regionTag(name: string, language: Language): string {
  return (language === "th" ? REGIONS[name]?.tagTh : REGIONS[name]?.tagEn) ?? "";
}

function qualityFlagLabel(flag: string, language: Language): string {
  return QUALITY_FLAG_COPY[flag]?.[language] ?? (language === "th"
    ? "รูปภาพไม่ผ่านเงื่อนไขคุณภาพที่ระบบใช้ประเมิน"
    : "The image did not meet the quality requirements for assessment.");
}

function getScoreLevel(score: number, language: Language): string {
  const copy = PAGE_COPY[language];
  if (score < 25) return copy.levelLow;
  if (score < 55) return copy.levelModerate;
  return copy.levelElevated;
}

function getScoreLevelClass(score: number): string {
  if (score < 25) return "level-low";
  if (score < 55) return "level-moderate";
  return "level-elevated";
}

function RegionCard({
  name,
  value,
  language,
}: {
  name: string;
  value: AreaScore;
  language: Language;
}) {
  const copy = PAGE_COPY[language];
  const label = regionLabel(name, language);
  const tag = regionTag(name, language);

  if (value.evaluated_pixels <= 0) {
    return (
      <div className="analysis-region analysis-region-card is-unscorable">
        <div className="analysis-region-header">
          <div className="analysis-region-title">
            <strong>{label}</strong>
            {tag && <span className="analysis-region-tag">{tag}</span>}
          </div>
          <span className="analysis-region-status">{copy.unscorable}</span>
        </div>
        <p className="analysis-region-empty">{copy.noRegionPixels}</p>
      </div>
    );
  }

  const areaPercent = value.wrinkle_area_ratio * 100;
  const clampedPercent = Math.min(100, Math.max(0, areaPercent));
  const intensityClass = areaPercent > 5 ? "is-prominent" : areaPercent > 0 ? "is-detected" : "is-clean";

  return (
    <div className={`analysis-region analysis-region-card ${intensityClass}`}>
      <div className="analysis-region-header">
        <div className="analysis-region-title">
          <strong>{label}</strong>
          {tag && <span className="analysis-region-tag">{tag}</span>}
        </div>
        <span className="analysis-region-area">{areaPercent.toFixed(2)}%</span>
      </div>
      <div
        className="analysis-region-track"
        role="progressbar"
        aria-label={`${copy.area}: ${label}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clampedPercent}
        aria-valuetext={`${areaPercent.toFixed(2)}% ${copy.percentageOfEvaluatedArea}`}
      >
        <span style={{ width: `${clampedPercent}%` }} />
      </div>
      <div className="analysis-region-footer">
        <span className="analysis-region-score-label">{copy.experimentalScore}</span>
        <strong className="analysis-region-score-val">{value.score.toFixed(1)} <small>/ 100</small></strong>
      </div>
    </div>
  );
}

export default function AnalysisResult({ onNewAnalysis }: { onNewAnalysis: () => void }) {
  const { language } = useLanguage();
  const copy = PAGE_COPY[language];
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [noAnalysis, setNoAnalysis] = useState(false);
  const [artifact, setArtifact] = useState<"overlay" | "mask">("overlay");
  const [artifactLoadError, setArtifactLoadError] = useState(false);
  const [expiryTick, setExpiryTick] = useState(0);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [zoomScale, setZoomScale] = useState(1);

  // Poll the analysis result; Label Studio task creation runs independently afterward.
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        // The signed cookie selects the latest analysis without exposing backend auth.
        const response = await fetch("/api/analysis", { cache: "no-store" });
        if (!response.ok) {
          if (response.status === 401) {
            if (!stopped) setNoAnalysis(true);
            return;
          }
          throw new Error("analysis-load-error");
        }
        const next = (await response.json()) as Analysis;
        // Ignore a response arriving after this page has unmounted.
        if (stopped) return;
        setNoAnalysis(false);
        setError("");
        setAnalysis(next);
        // Stop polling once the worker reaches a terminal status.
        if (next.status === "queued" || next.status === "running") {
          timer = setTimeout(poll, 2500);
        }
      } catch {
        if (!stopped) setError("analysis-load-error");
      }
    }
    poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, []);

  const score = analysis?.result?.derived_score ?? analysis?.result?.experimental_score;
  const expiresAt = analysis?.result?.artifacts_expires_at;
  const allRegions = Object.entries(score?.regions ?? {});
  const evaluableRegions = allRegions
    .filter(([, value]) => value.evaluated_pixels > 0)
    .sort(([, left], [, right]) => right.wrinkle_area_ratio - left.wrinkle_area_ratio);
  const unevaluableRegions = allRegions.filter(([, value]) => value.evaluated_pixels <= 0);
  const displayedRegions = [...evaluableRegions, ...unevaluableRegions];
  const hasScorableOverall = Boolean(score && score.overall.evaluated_pixels > 0);
  const expiryLabel = expiresAt ? formatArtifactExpiry(expiresAt, language) : null;

  // Re-render at expiry so the artifact message changes even if the page stays open.
  useEffect(() => {
    if (analysis?.status !== "completed") return;
    if (!expiresAt) return;
    const expiration = Date.parse(expiresAt);
    if (!Number.isFinite(expiration)) return;
    let expiryTimer: ReturnType<typeof setTimeout>;
    const checkExpiry = () => {
      const remaining = expiration - Date.now();
      if (remaining <= 0) {
        setExpiryTick(Date.now());
        return;
      }
      expiryTimer = setTimeout(checkExpiry, Math.min(remaining, 2_147_483_647));
    };
    expiryTimer = setTimeout(checkExpiry, Math.max(0, Math.min(expiration - Date.now(), 2_147_483_647)));
    return () => clearTimeout(expiryTimer);
  }, [analysis?.status, expiresAt]);

  // Handle escape key to close zoom modal
  useEffect(() => {
    if (!zoomOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [zoomOpen]);

  const currentArtifactAvailability = getArtifactAvailability(expiresAt, expiryTick);
  const artifactAvailability: ArtifactAvailability = currentArtifactAvailability === "available" && artifactLoadError
    ? "load-error"
    : currentArtifactAvailability;

  return (
    <section className="page-content workspace-panel analysis-page analysis-page--face">
      <div className="analysis-page-heading">
        <div className="analysis-heading-main">
          <span className="analysis-heading-badge">
            <Sparkles size={13} aria-hidden="true" />
            <span>{copy.analysisEyebrow}</span>
          </span>
          <h2>{copy.resultTitle}</h2>
          <div className="analysis-heading-meta">
            {analysis && (
              <span className="analysis-chip">
                <Clock size={13} aria-hidden="true" />
                <span>{analysisDetail(analysis, language)}</span>
              </span>
            )}
            {analysis?.status === "completed" && (
              <span className="analysis-chip chip-success">
                <CheckCircle2 size={13} aria-hidden="true" />
                <span>{copy.qualityVerified}</span>
              </span>
            )}
            <span className="analysis-chip chip-privacy">
              <Lock size={13} aria-hidden="true" />
              <span>{copy.privacyBadge}</span>
            </span>
          </div>
        </div>
        <nav className="analysis-page-actions" aria-label={copy.actions}>
          <button className="primary-button" type="button" onClick={onNewAnalysis}>
            {copy.retryAnalysis} <ArrowRight size={16} aria-hidden="true" />
          </button>
          <Link className="secondary-button" href="/">
            {copy.backHome}
          </Link>
        </nav>
      </div>

      {noAnalysis && (
        <div className="analysis-empty-state" role="status">
          <div className="analysis-empty-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="5" width="18" height="14" rx="2" />
              <circle cx="12" cy="12" r="3" />
              <path d="m7 5 1.5-2h7L17 5" />
            </svg>
          </div>
          <div>
            <h3>{copy.noAnalysis}</h3>
            <p>{copy.noAnalysisBody}</p>
          </div>
        </div>
      )}

      {error && (
        <div className="analysis-state-message" role="alert">
          <h3>{copy.loadErrorTitle}</h3>
          <p>{copy.loadError}</p>
          <button className="secondary-button" type="button" onClick={() => window.location.reload()}>
            {copy.retryLoad}
          </button>
        </div>
      )}

      {!analysis && !error && !noAnalysis && <div className="analysis-state-message" role="status">{copy.loading}</div>}

      {analysis && (analysis.status === "queued" || analysis.status === "running") && (
        <div className="result-wait" role="status">{copy.processing}</div>
      )}

      {analysis?.status === "rejected" && (
        <div className="result-wait" role="alert">
          <h2>{copy.rejectedTitle}</h2>
          {analysis.quality_flags.length ? (
            <ul className="quality-flag-list">
              {[...new Set(analysis.quality_flags)].map((flag) => (
                <li key={flag}>{qualityFlagLabel(flag, language)}</li>
              ))}
            </ul>
          ) : (
            <p>{copy.rejectedBody}</p>
          )}
          <button className="primary-button" type="button" onClick={onNewAnalysis}>
            {copy.chooseImage} →
          </button>
        </div>
      )}

      {analysis?.status === "failed" && (
        <div className="result-wait" role="alert">
          <h2>{copy.failedTitle}</h2>
          <p>{copy.failedBody}</p>
          <button className="primary-button" type="button" onClick={onNewAnalysis}>
            {copy.tryAgain} →
          </button>
        </div>
      )}

      {analysis?.status === "completed" && (
        score && hasScorableOverall ? (
          <>
            <div className="analysis-result-grid">
              {/* Left Column: Interactive Image Studio (Sticky on Desktop) */}
              <section className="analysis-section analysis-image-section" aria-labelledby="analysis-image-heading">
                <div className="analysis-section-heading">
                  <div>
                    <h3 id="analysis-image-heading">{copy.imageHeading}</h3>
                    <p className="analysis-image-subheading">{copy.imageSubheading}</p>
                  </div>
                  {artifactAvailability === "available" && (
                    <button
                      type="button"
                      className="artifact-zoom-button"
                      onClick={() => { setZoomScale(1); setZoomOpen(true); }}
                      aria-label={copy.zoom}
                      title={copy.zoom}
                    >
                      <Maximize2 size={15} aria-hidden="true" />
                      <span>{copy.zoom}</span>
                    </button>
                  )}
                </div>

                <div className="artifact-tabs" role="group" aria-label={copy.artifactControls}>
                  <button
                    type="button"
                    aria-pressed={artifact === "overlay"}
                    className={artifact === "overlay" ? "active" : ""}
                    onClick={() => { setArtifact("overlay"); setArtifactLoadError(false); }}
                  >
                    <Eye size={15} aria-hidden="true" />
                    <span>{copy.overlay}</span>
                  </button>
                  <button
                    type="button"
                    aria-pressed={artifact === "mask"}
                    className={artifact === "mask" ? "active" : ""}
                    onClick={() => { setArtifact("mask"); setArtifactLoadError(false); }}
                  >
                    <Layers size={15} aria-hidden="true" />
                    <span>{copy.mask}</span>
                  </button>
                </div>

                <figure
                  className={`overlay-card result-artifact${artifactAvailability === "available" ? " is-interactive" : ""}`}
                  aria-live="polite"
                  onClick={artifactAvailability === "available" ? () => { setZoomScale(1); setZoomOpen(true); } : undefined}
                  onKeyDown={artifactAvailability === "available" ? (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setZoomScale(1);
                      setZoomOpen(true);
                    }
                  } : undefined}
                  tabIndex={artifactAvailability === "available" ? 0 : undefined}
                  role={artifactAvailability === "available" ? "button" : undefined}
                  aria-label={artifactAvailability === "available" ? copy.clickToZoom : undefined}
                >
                  {artifactAvailability === "available" ? (
                    <>
                      <Image
                        key={artifact}
                        className="analysis-result-image"
                        unoptimized
                        width={512}
                        height={512}
                        src={`/api/analysis?artifact=${artifact}`}
                        alt={artifact === "overlay" ? copy.overlayAlt : copy.maskAlt}
                        onError={() => setArtifactLoadError(true)}
                      />
                      <span className="artifact-click-hint" aria-hidden="true">
                        <ZoomIn size={14} />
                        <span>{copy.clickToZoom}</span>
                      </span>
                    </>
                  ) : (
                    <p role={artifactAvailability === "load-error" || artifactAvailability === "expired" ? "alert" : "status"}>
                      {artifactAvailability === "expired" && copy.expired}
                      {artifactAvailability === "unavailable" && copy.unavailable}
                      {artifactAvailability === "load-error" && copy.imageLoadError}
                    </p>
                  )}
                </figure>

                <div className="analysis-artifact-footer">
                  <div className="analysis-legend-row" aria-label={copy.legendTitle}>
                    <span className="legend-chip">
                      <span className="legend-dot dot-wrinkle" aria-hidden="true" />
                      <span>{copy.legendWrinkles}</span>
                    </span>
                    <span className="legend-chip">
                      <span className="legend-dot dot-evaluated" aria-hidden="true" />
                      <span>{copy.legendEvaluated}</span>
                    </span>
                  </div>

                  <figcaption className="analysis-caption">
                    <Clock size={13} aria-hidden="true" className="caption-clock" />
                    <span>
                      {copy.overlayCaption}
                      {artifactAvailability === "available" && expiryLabel && ` · ${copy.expiryPrefix} ${expiryLabel} (${copy.thailandTime})`}
                      {artifactAvailability === "expired" && ` · ${copy.artifactExpired}`}
                    </span>
                  </figcaption>
                </div>
              </section>

              {/* Right Column: Facial Metrics & Regional Breakdown */}
              <div className="analysis-results-column">
                {/* Hero Summary KPI Card */}
                <section className="analysis-summary" aria-labelledby="analysis-score-heading">
                  <div className="analysis-summary-header">
                    <div className="analysis-summary-title-wrap">
                      <h3 id="analysis-score-heading">{copy.summaryCardTitle}</h3>
                      <p className="analysis-summary-sub">{copy.markedAreaExplanation}</p>
                    </div>
                  </div>

                  <div className="analysis-summary-values">
                    <div className="analysis-kpi-tile analysis-coverage">
                      <div className="kpi-label-wrap">
                        <span className="kpi-label">{copy.markedArea}</span>
                        <span className="kpi-tag">{copy.percentageOfEvaluatedArea}</span>
                      </div>
                      <div className="kpi-number-wrap">
                        <strong>{(score.overall.wrinkle_area_ratio * 100).toFixed(2)}%</strong>
                      </div>
                      <div className="kpi-mini-track" aria-hidden="true">
                        <span style={{ width: `${Math.min(100, Math.max(0, score.overall.wrinkle_area_ratio * 100))}%` }} />
                      </div>
                    </div>

                    <div className="analysis-kpi-tile analysis-total">
                      <div className="kpi-label-wrap">
                        <span className="kpi-label">{copy.experimentalScore}</span>
                        <span className={`kpi-level-badge ${getScoreLevelClass(score.overall.score)}`}>
                          {getScoreLevel(score.overall.score, language)}
                        </span>
                      </div>
                      <div className="kpi-number-wrap">
                        <strong>{score.overall.score.toFixed(1)} <small>/ 100</small></strong>
                      </div>
                      <div className="kpi-note">{copy.scoreExplanationBrief}</div>
                    </div>
                  </div>

                  <div className="analysis-summary-note">
                    <Info size={15} aria-hidden="true" className="note-icon" />
                    <p>{copy.scoreExplanation}</p>
                  </div>
                </section>

                {/* Facial Regions Breakdown Card */}
                <section className="analysis-section analysis-region-section" aria-labelledby="analysis-regions-heading">
                  <div className="analysis-section-heading">
                    <div>
                      <h3 id="analysis-regions-heading">{copy.regionsHeading}</h3>
                      <p className="analysis-section-intro">{copy.regionExplanation}</p>
                    </div>
                    <span className="regions-count-badge">
                      {copy.regionsSummary(evaluableRegions.length, allRegions.length)}
                    </span>
                  </div>

                  {evaluableRegions.length > 0 ? (
                    <div className="analysis-regions analysis-regions-grid">
                      {displayedRegions.map(([name, value]) => (
                        <RegionCard key={name} name={name} value={value} language={language} />
                      ))}
                    </div>
                  ) : (
                    <p className="analysis-section-intro">{copy.noRegionPixels}</p>
                  )}

                  <details className="analysis-extra-regions">
                    <summary>{copy.viewTechnicalData}</summary>
                    <div className="analysis-technical-body">
                      <p className="analysis-pixel-count-label">{copy.pixelCounts}</p>
                      <dl className="analysis-region-detail-list">
                        {displayedRegions.map(([name, value]) => (
                          <div className="analysis-region-detail" key={name}>
                            <dt>
                              <span>{regionLabel(name, language)}</span>
                              {regionTag(name, language) && (
                                <small className="analysis-detail-tag">{regionTag(name, language)}</small>
                              )}
                            </dt>
                            <dd>
                              {value.evaluated_pixels > 0 ? (
                                <>
                                  {value.wrinkle_pixels.toLocaleString(language === "th" ? "th-TH" : "en-GB")} / {value.evaluated_pixels.toLocaleString(language === "th" ? "th-TH" : "en-GB")} {copy.pixels}
                                  <small>{(value.wrinkle_area_ratio * 100).toFixed(2)}% · {value.score.toFixed(1)} / 100</small>
                                </>
                              ) : copy.noRegionPixels}
                            </dd>
                          </div>
                        ))}
                      </dl>

                      <div className="analysis-method-content">
                        <h4>{copy.method}</h4>
                        <p>{copy.ratioFormula}</p>
                        <p>{copy.scoreFormula} <code>{score.formula}</code>. {copy.decimalNote}</p>
                        <p>{copy.thisImage} {score.overall.wrinkle_pixels.toLocaleString(language === "th" ? "th-TH" : "en-GB")} ÷ {score.overall.evaluated_pixels.toLocaleString(language === "th" ? "th-TH" : "en-GB")} {copy.pixels} = {(score.overall.wrinkle_area_ratio * 100).toFixed(2)}% · {copy.experimentalScore.toLowerCase()} {score.overall.score.toFixed(1)} / 100.</p>
                        <p>{copy.scoreCapped}</p>
                      </div>
                    </div>
                  </details>
                </section>
              </div>
            </div>

            {/* Dedicated Full-Width Guidance & Recommendations Section */}
            <section className="analysis-recommendation-section" aria-labelledby="analysis-recommendations-heading">
              <div className="analysis-section-heading">
                <div className="recommendation-header-content">
                  <span className="recommendation-badge">
                    <Sparkles size={13} aria-hidden="true" />
                    <span>{copy.recommendationsEyebrow}</span>
                  </span>
                  <h3 id="analysis-recommendations-heading">{copy.recommendations}</h3>
                  <p className="recommendation-header-desc">{copy.recommendationsDesc}</p>
                </div>
              </div>
              <RecommendationPanel language={language} />
            </section>

            {/* Medical / Clinical Disclaimer */}
            <div className="analysis-disclaimer">
              <ShieldCheck size={22} aria-hidden="true" className="disclaimer-icon" />
              <div className="disclaimer-content">
                <strong>{copy.disclaimerTitle}</strong>
                <p>{copy.disclaimer}</p>
              </div>
            </div>

            {/* Lightbox / Zoom Modal for Desktop Inspection */}
            {zoomOpen && (
              <div
                className="analysis-zoom-modal"
                role="dialog"
                aria-modal="true"
                aria-label={copy.zoom}
                onClick={(e) => {
                  if (e.target === e.currentTarget) setZoomOpen(false);
                }}
              >
                <div className="analysis-zoom-dialog">
                  <div className="analysis-zoom-header">
                    <div className="analysis-zoom-tabs" role="group" aria-label={copy.artifactControls}>
                      <button
                        type="button"
                        className={artifact === "overlay" ? "active" : ""}
                        onClick={() => { setArtifact("overlay"); setArtifactLoadError(false); }}
                      >
                        <Eye size={15} aria-hidden="true" />
                        <span>{copy.overlay}</span>
                      </button>
                      <button
                        type="button"
                        className={artifact === "mask" ? "active" : ""}
                        onClick={() => { setArtifact("mask"); setArtifactLoadError(false); }}
                      >
                        <Layers size={15} aria-hidden="true" />
                        <span>{copy.mask}</span>
                      </button>
                    </div>

                    <div className="analysis-zoom-controls">
                      <button
                        type="button"
                        className="zoom-tool-btn"
                        onClick={() => setZoomScale((s) => Math.min(2.5, +(s + 0.25).toFixed(2)))}
                        aria-label={copy.zoomIn}
                        title={copy.zoomIn}
                      >
                        <ZoomIn size={18} />
                      </button>
                      <button
                        type="button"
                        className="zoom-tool-btn"
                        onClick={() => setZoomScale((s) => Math.max(0.75, +(s - 0.25).toFixed(2)))}
                        aria-label={copy.zoomOut}
                        title={copy.zoomOut}
                      >
                        <ZoomOut size={18} />
                      </button>
                      <button
                        type="button"
                        className="zoom-tool-btn zoom-tool-reset"
                        onClick={() => setZoomScale(1)}
                        aria-label={copy.zoomReset}
                        title={copy.zoomReset}
                      >
                        {Math.round(zoomScale * 100)}%
                      </button>
                      <button
                        type="button"
                        className="zoom-tool-btn zoom-tool-close"
                        onClick={() => setZoomOpen(false)}
                        aria-label={copy.closeZoom}
                        title={copy.closeZoom}
                      >
                        <X size={20} />
                      </button>
                    </div>
                  </div>

                  <div className="analysis-zoom-body">
                    <div className="analysis-zoom-canvas">
                      <Image
                        key={`zoom-${artifact}`}
                        className="analysis-zoom-image"
                        unoptimized
                        width={1024}
                        height={1024}
                        src={`/api/analysis?artifact=${artifact}`}
                        alt={artifact === "overlay" ? copy.overlayAlt : copy.maskAlt}
                        style={{ transform: `scale(${zoomScale})` }}
                      />
                    </div>
                  </div>

                  <div className="analysis-zoom-footer">
                    <span className="analysis-zoom-caption">{copy.overlayCaption}</span>
                    {expiryLabel && <span className="analysis-zoom-expiry">{copy.expiryPrefix} {expiryLabel}</span>}
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="result-wait" role="status">
            <h2>{copy.noScore}</h2>
            <button className="primary-button" type="button" onClick={onNewAnalysis}>
              {copy.retryAnalysis} →
            </button>
            <section className="analysis-recommendation-section" aria-labelledby="analysis-recommendations-heading">
              <h3 id="analysis-recommendations-heading">{copy.recommendations}</h3>
              <RecommendationPanel language={language} />
            </section>
          </div>
        )
      )}
    </section>
  );
}
