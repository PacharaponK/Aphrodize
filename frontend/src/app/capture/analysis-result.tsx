"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Clock,
  Eye,
  Info,
  Layers,
  Lock,
  Maximize2,
  ShieldCheck,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { RecommendationPanel } from "@/app/recommendation/recommendation-panel";
import "../result-detail/result-detail.css";
import { useLanguage, type Language } from "@/components/language-provider";

type AreaScore = { score: number; wrinkle_area_ratio: number; wrinkle_pixels: number; evaluated_pixels: number };
type Score = { overall: AreaScore; regions: Record<string, AreaScore>; formula: string; disclaimer: string; roi_version?: string };
type Result = {
  status: string;
  derived_score?: Score | null;
  experimental_score?: Score | null;
  artifacts_expires_at?: string;
  recommendation_gate?: { eligible: boolean; reasons: string[] };
  model_output?: { personalized_outline_available?: boolean; regional_geometry_status?: "available" | "unavailable" | "legacy_fixed"; regional_map_version?: "wrinkle-only-sketch-v1" | "photo-doodle-wrinkle-v2" | "head-region-area-v3" | null };
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
    imageSubheading: "เปิดดูบริเวณที่โมเดลทำเครื่องหมายในภาพนี้",
    artifactControls: "เลือกรูปแบบภาพผลวิเคราะห์",
    overlay: "ภาพซ้อนตำแหน่ง",
    mask: "เฉพาะพื้นที่ตรวจพบ",
    overlayAlt: "ภาพใบหน้าพร้อมบริเวณที่โมเดลทำเครื่องหมาย",
    maskAlt: "ภาพแสดงเฉพาะบริเวณที่โมเดลทำเครื่องหมาย",
    expired: "ภาพผลวิเคราะห์หมดอายุแล้ว กรุณาวิเคราะห์ภาพใหม่เพื่อดูภาพประกอบ",
    unavailable: "ไม่มีภาพผลวิเคราะห์ที่เปิดดูได้ กรุณาวิเคราะห์ภาพใหม่",
    imageLoadError: "โหลดภาพผลวิเคราะห์ไม่สำเร็จ กรุณาลองอีกครั้งหรือวิเคราะห์ภาพใหม่",
    retryImage: "ลองโหลดภาพอีกครั้ง",
    overlayCaption: "สีบนภาพแสดงบริเวณที่โมเดลทำเครื่องหมาย",
    expiryPrefix: "ภาพส่วนตัวเปิดดูได้ถึง",
    thailandTime: "เวลาไทย",
    artifactExpired: "ภาพหมดอายุการเข้าถึงแล้ว",
    markedArea: "พื้นที่ที่โมเดลทำเครื่องหมาย",
    markedAreaExplanation: "สัดส่วนพิกเซลที่โมเดลทำเครื่องหมายในพื้นที่ใบหน้าที่ประเมิน ไม่ใช่คะแนนผิวหรือการวินิจฉัย",
    experimentalScore: "คะแนนเชิงทดลอง",
    scoreExplanation: "คะแนนจากสัดส่วนพื้นที่ มีเพดาน 100 ค่าสูงหมายถึงพื้นที่ทำเครื่องหมายมากขึ้น ไม่ใช่ผิวดีขึ้นหรือแย่ลง",
    scoreExplanationBrief: "คำนวณจากสัดส่วนพื้นที่พิกเซล (เพดาน 100)",
    regionsHeading: "การกระจายตัวตามบริเวณใบหน้า",
    regionsScored: "บริเวณที่มีคะแนน",
    regionExplanation: "4 บริเวณที่มีสัดส่วนสูงสุด ดูทั้งหมดในรายละเอียด",
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
    disclaimerTitle: "เกี่ยวกับการวัดจากภาพนี้",
    disclaimer: "ผลทดลองจากภาพ ไม่ใช่การวินิจฉัยหรือการประเมินสุขภาพผิว ยังไม่ผ่านการรับรองทางคลินิก",
    noScore: "ไม่มีคะแนนสำหรับภาพนี้",
    queued: "รอประมวลผล",
    running: "กำลังประมวลผล",
    analyzed: "วิเคราะห์เมื่อ",
    regionsSummary: (scored: number, total: number) => `ประเมินได้ ${scored} / ${total} บริเวณ`,
    analysisEyebrow: "การวิเคราะห์ภาพถ่ายใบหน้าด้วย AI",
    qualityVerified: "ผ่านเกณฑ์คุณภาพภาพถ่าย",
    zoom: "ขยายดูภาพ",
    zoomIn: "ขยาย",
    zoomOut: "ย่อ",
    zoomReset: "ขนาดปกติ",
    closeZoom: "ปิดภาพขยาย",
    clickToZoom: "คลิกเพื่อขยายดูภาพ",
    legendWrinkles: "เส้นสี: บริเวณที่โมเดลทำเครื่องหมาย",
    legendEvaluated: "กรอบสว่าง: ขอบเขตใบหน้าที่ประเมิน",
    legendTitle: "คำอธิบายภาพ",
    viewTechnicalData: "ดูทุกบริเวณ พิกเซล และวิธีคำนวณ",
    summaryCardTitle: "สิ่งที่โมเดลทำเครื่องหมาย",
    overviewTitle: "ภาพรวมการวิเคราะห์ผิว",
    overviewScope: "ตรวจพื้นที่ริ้วรอยจากภาพนี้เท่านั้น",
    mapTitle: "ตำแหน่งที่ควรเปิดดู",
    mapNote: "แผนภาพมาตรฐาน ไม่ใช่รูปหน้าของคุณ แรเงาบริเวณที่มีผลตรวจ ไม่ใช่ความรุนแรงหรือพิกเซลจริง ดูตำแหน่งจริงใน overlay/mask",
    personalOutlineNote: "โครงหน้าแบบย่อจาก landmarks ของภาพคุณ แรเงาบริเวณที่มีผลตรวจ ไม่ใช่ความรุนแรงหรือพิกเซลจริง ดูพิกเซลใน overlay/mask",
    personalOutlineUnavailable: "โครงหน้ารายบุคคลไม่พร้อมแสดง ด้านล่างเป็นแผนภาพมาตรฐานแทน",
    regionRank: "ลำดับตามสัดส่วนพื้นที่",
    landmarkMapNote: "สเก็ตช์ใบหน้าจาก landmarks ของภาพนี้ สีชมพูแสดงเฉพาะพิกเซลริ้วรอยที่โมเดลทำเครื่องหมายในพื้นที่ประเมิน ไม่ใช่ระดับความรุนแรงหรือการวินิจฉัย",
    photoSketchNote: "ภาพเส้นขอบแปลงจากภาพที่คุณอัปโหลดในกรอบเดียวกับการวิเคราะห์ ไม่มีแรเงาดินสอ เส้นขอบไม่ใช่ริ้วรอยที่ตรวจพบ สีชมพูแสดงเฉพาะ mask ริ้วรอยภายในพื้นที่ประเมิน ไม่ใช่การวินิจฉัย",
    headRegionNote: "โครงหน้าจาก landmarks ของภาพคุณ ไม่มีผมหรือพื้นหลัง สีชมพูแสดงบริเวณที่มีผลตรวจ ไม่ใช่พิกเซลริ้วรอยทั้งหมด ดูพิกเซลจริงใน overlay/mask ไม่ใช่การวินิจฉัย",
    legacyLandmarkMapNote: "แผนภาพรุ่นเดิม: สีอ่อนแสดงพื้นที่ประเมิน ไม่ใช่พื้นที่ริ้วรอยทั้งหมด สีเข้มแสดงพิกเซลที่โมเดลทำเครื่องหมาย วิเคราะห์ภาพใหม่เพื่อดูสเก็ตช์ที่แสดงเฉพาะริ้วรอย",
    mapUnavailable: "ยังเปิดแผนภาพ landmarks ไม่ได้ ค่ารายบริเวณยังดูได้ในรายการ",
    noLandmarkRegions: "ตรวจตำแหน่งใบหน้าในภาพนี้ไม่ได้ จึงไม่คำนวณค่ารายบริเวณ ลองภาพใหม่ที่เห็นใบหน้าชัดเจน",
    measuredRegions: "บริเวณที่ประเมินได้",
    largestRegion: "สัดส่วนสูงสุดรายบริเวณ",
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
    imageSubheading: "Inspect the areas marked by the model in this image.",
    artifactControls: "Choose an analysis image view",
    overlay: "Marked areas",
    mask: "Mask only",
    overlayAlt: "Face image with the areas marked by the model",
    maskAlt: "Image showing only the areas marked by the model",
    expired: "This analysis image has expired. Analyze a new image to view an artifact.",
    unavailable: "No analysis image is available to view. Analyze a new image.",
    imageLoadError: "Could not load this analysis image. Try again or analyze a new image.",
    retryImage: "Retry image",
    overlayCaption: "Color shows the areas marked by the model.",
    expiryPrefix: "Private image available until",
    thailandTime: "Thailand time",
    artifactExpired: "Image access has expired.",
    markedArea: "Marked-area proportion",
    markedAreaExplanation: "Share of evaluated face pixels marked by the model—not a skin grade or diagnosis.",
    experimentalScore: "Experimental score",
    scoreExplanation: "Area-based score, capped at 100. Higher means more marked area, not better or worse skin.",
    scoreExplanationBrief: "Calculated from pixel area proportion (capped at 100)",
    regionsHeading: "Marked areas by region",
    regionsScored: "regions scored",
    regionExplanation: "Top four regions by marked proportion. Expand details for all regions.",
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
    disclaimerTitle: "About these measurements",
    disclaimer: "Experimental image measurements—not a diagnosis or skin-health assessment. Not clinically validated.",
    noScore: "No score is available for this image.",
    queued: "Queued for processing",
    running: "Processing",
    analyzed: "Analyzed",
    regionsSummary: (scored: number, total: number) => `${scored} / ${total} regions measurable`,
    analysisEyebrow: "AI-Powered Vision Analysis",
    qualityVerified: "Image quality passed",
    zoom: "Zoom image",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    zoomReset: "Reset",
    closeZoom: "Close zoom",
    clickToZoom: "Click to inspect in detail",
    legendWrinkles: "Colored lines: Areas marked by the model",
    legendEvaluated: "Bright area: Evaluated face region",
    legendTitle: "Image legend",
    viewTechnicalData: "All regions, pixels & calculation details",
    summaryCardTitle: "What the model marked",
    overviewTitle: "Skin analysis overview",
    overviewScope: "Wrinkle-area measurements from this image only",
    mapTitle: "Areas to inspect",
    mapNote: "Standard face diagram, not your face shape. Hatching shows regions with detections, not severity or exact pixels. See overlay/mask for exact marks.",
    personalOutlineNote: "Simplified outline from your image's landmarks. Hatching shows regions with detections, not severity or exact pixels. See overlay/mask for exact pixels.",
    personalOutlineUnavailable: "Your personalized outline is unavailable. A standard face diagram is shown below instead.",
    regionRank: "Ranked by marked proportion",
    landmarkMapNote: "Head sketch from this image's landmarks. Pink shows only model-marked wrinkle pixels within evaluated regions, not severity or a diagnosis.",
    photoSketchNote: "Outline converted from your uploaded image in the analysis frame, without pencil shading. Outlines are not wrinkle detections. Pink shows only the wrinkle mask within evaluated regions, not a diagnosis.",
    headRegionNote: "Head outline from your image's landmarks, without hair or background. Pink shows regions with detections, not exact wrinkle pixels. See overlay/mask for exact pixels. Not a diagnosis.",
    legacyLandmarkMapNote: "Earlier map: pale shading shows evaluated regions, not wrinkle coverage. Dark pixels show model marks. Analyze a new image for a wrinkle-only sketch.",
    mapUnavailable: "The landmark map is unavailable. Regional measurements remain in the list.",
    noLandmarkRegions: "Facial landmarks could not be measured in this image, so regional values are withheld. Try a clearer face image.",
    measuredRegions: "Regions measured",
    largestRegion: "Largest regional proportion",
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

// Only known model region identifiers have schematic locations. Image-left/right
// refer to the displayed image, not the person's anatomical left/right.
const REGION_SHAPES: Record<string, string> = {
  forehead: "M68 91 Q120 53 172 91 L168 121 Q120 105 72 121 Z",
  glabella: "M110 124 Q120 117 130 124 L131 145 L109 145 Z",
  image_left_periocular: "M62 142 Q83 124 105 142 L105 159 Q82 170 62 156 Z",
  image_right_periocular: "M135 142 Q157 124 178 142 L178 156 Q158 170 135 159 Z",
  image_left_cheek: "M62 173 Q82 163 100 177 L98 207 Q76 213 64 197 Z",
  image_right_cheek: "M140 177 Q158 163 178 173 L176 197 Q164 213 142 207 Z",
  nasolabial: "M105 181 L110 187 L98 222 L91 218 Z M130 187 L135 181 L149 218 L142 222 Z",
  perioral: "M97 225 Q120 212 143 225 L145 243 Q120 258 95 243 Z",
};

function FaceRegionMap({ regions, language }: { regions: [string, AreaScore][]; language: Language }) {
  const copy = PAGE_COPY[language];
  const mapped = regions.filter(([name, value]) => REGION_SHAPES[name] && value.evaluated_pixels > 0 && value.wrinkle_pixels > 0 && value.wrinkle_area_ratio > 0);
  return (
    <figure className="analysis-face-map">
      <svg viewBox="0 0 240 310" role="img" aria-label={copy.mapTitle}>
        <title>{copy.mapTitle}</title>
        <defs><pattern id="face-roi-hatching" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="4" height="4" fill="var(--primary-soft)" /><path d="M0 0 V4" stroke="var(--primary)" strokeWidth=".6" /></pattern></defs>
        <desc>{copy.mapNote} {mapped.map(([name, value]) => `${regionLabel(name, language)}: ${(value.wrinkle_area_ratio * 100).toFixed(2)}%`).join("; ")}</desc>
        {mapped.map(([name, value]) => {
          return <path key={name} d={REGION_SHAPES[name]} data-face-region={name} style={{ fill: "url(#face-roi-hatching)" }} className="face-map-zone is-marked">
            <title>{regionLabel(name, language)}: {(value.wrinkle_area_ratio * 100).toFixed(2)}%</title>
          </path>;
        })}
        <path className="face-map-outline" d="M120 27 C78 27 55 52 53 98 C51 125 54 158 59 185 C64 222 91 261 120 269 C149 261 176 222 181 185 C186 158 189 125 187 98 C185 52 162 27 120 27 Z M53 145 C43 131 37 142 42 161 C43 173 48 184 59 191 M187 145 C197 131 203 142 198 161 C197 173 192 184 181 191 M87 248 C89 264 89 278 84 288 L65 300 M153 248 C151 264 151 278 156 288 L175 300" />
        <path className="face-map-features" d="M65 128 C75 120 90 120 102 126 M138 126 C150 120 165 120 175 128 M65 146 C76 135 91 135 102 146 C91 155 76 156 65 146 Z M138 146 C149 135 164 135 175 146 C164 156 149 155 138 146 Z M65 150 Q80 160 97 152 M143 152 Q160 160 175 150 M114 153 C112 168 107 180 107 189 Q110 193 114 190 M126 153 C128 168 133 180 133 189 Q130 193 126 190 M114 195 Q120 199 126 195 M98 222 C107 221 114 215 120 218 C126 215 133 221 142 222 Q132 224 120 223 Q108 224 98 222 M101 225 Q120 238 139 225 M108 248 Q120 252 132 248" />
        <g className="face-map-features" aria-hidden="true">
          <circle cx="83" cy="145" r="6" /><circle cx="157" cy="145" r="6" />
          <circle cx="83" cy="145" r="2" fill="var(--muted)" /><circle cx="157" cy="145" r="2" fill="var(--muted)" />
        </g>
      </svg>
      <figcaption><strong>{copy.mapTitle}</strong><span>{copy.mapNote}</span></figcaption>
    </figure>
  );
}

function RegionCard({
  name,
  value,
  language,
  rank,
}: {
  name: string;
  value: AreaScore;
  language: Language;
  rank?: number;
}) {
  const copy = PAGE_COPY[language];
  const label = regionLabel(name, language);

  if (value.evaluated_pixels <= 0) {
    return (
      <div className="analysis-region analysis-region-card is-unscorable">
        <div className="analysis-region-header">
          <div className="analysis-region-title">
            <strong>{label}</strong>
          </div>
          <span className="analysis-region-status">{copy.unscorable}</span>
        </div>
        <p className="analysis-region-empty">{copy.noRegionPixels}</p>
      </div>
    );
  }

  const areaPercent = value.wrinkle_area_ratio * 100;
  const clampedPercent = Math.min(100, Math.max(0, areaPercent));

  return (
    <div className="analysis-region analysis-region-card">
      <div className="analysis-region-header">
        <div className="analysis-region-title">
          {rank && <span className="analysis-region-rank" aria-label={`${copy.regionRank}: ${rank}`}>{rank}</span>}
          <strong>{label}</strong>
        </div>
        <span className="analysis-region-area">{areaPercent.toFixed(2)}%</span>
      </div>
      <div
        className="analysis-region-track"
        role="meter"
        aria-label={`${copy.area}: ${label}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clampedPercent}
        aria-valuetext={`${areaPercent.toFixed(2)}% ${copy.percentageOfEvaluatedArea}`}
      >
        <span style={{ width: `${clampedPercent}%` }} />
      </div>
    </div>
  );
}

export default function AnalysisResult({ onNewAnalysis, onReady, view }: {
  onNewAnalysis: () => void;
  onReady: (ready: boolean) => void;
  view: "results" | "products";
}) {
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
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [artifactAttempt, setArtifactAttempt] = useState(0);
  const [outlineError, setOutlineError] = useState("");
  const zoomDialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    onReady(analysis?.status === "completed" && !error && !noAnalysis);
  }, [analysis?.status, error, noAnalysis, onReady]);

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
            if (!stopped) { setNoAnalysis(true); setAnalysis(null); }
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
  }, [loadAttempt]);

  const score = analysis?.result?.derived_score ?? analysis?.result?.experimental_score;
  const expiresAt = analysis?.result?.artifacts_expires_at;
  const allRegions = Object.entries(score?.regions ?? {});
  const evaluableRegions = allRegions
    .filter(([, value]) => value.evaluated_pixels > 0)
    .sort(([, left], [, right]) => right.wrinkle_area_ratio - left.wrinkle_area_ratio);
  const unevaluableRegions = allRegions.filter(([, value]) => value.evaluated_pixels <= 0);
  const displayedRegions = [...evaluableRegions, ...unevaluableRegions];
  const primaryRegions = evaluableRegions.slice(0, 4);
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
        setZoomOpen(false);
        return;
      }
      expiryTimer = setTimeout(checkExpiry, Math.min(remaining, 2_147_483_647));
    };
    expiryTimer = setTimeout(checkExpiry, Math.max(0, Math.min(expiration - Date.now(), 2_147_483_647)));
    return () => clearTimeout(expiryTimer);
  }, [analysis?.status, expiresAt]);

  const currentArtifactAvailability = getArtifactAvailability(expiresAt, expiryTick);
  const artifactAvailability: ArtifactAvailability = currentArtifactAvailability === "available" && artifactLoadError
    ? "load-error"
    : currentArtifactAvailability;
  const artifactSource = `/api/analysis?artifact=${artifact}${artifactAttempt ? `&retry=${artifactAttempt}` : ""}`;
  const zoomVisible = zoomOpen && artifactAvailability === "available";

  // Keep keyboard focus inside the image viewer and restore it when closing.
  useEffect(() => {
    if (!zoomVisible) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = zoomDialogRef.current;
    dialog?.querySelector<HTMLButtonElement>("[data-zoom-close]")?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomOpen(false);
      if (e.key !== "Tab" || !dialog) return;
      const controls = [...dialog.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [zoomVisible]);

  return (
    <section className="page-content workspace-panel analysis-page analysis-page--face">
      <div className="analysis-page-heading">
        <div className="analysis-heading-main">
          <h2>{view === "products" ? (language === "th" ? "ผลิตภัณฑ์ที่แนะนำ" : "Recommended products") : copy.resultTitle}</h2>
          {view === "results" && <p className="analysis-heading-intro">{copy.resultIntro}</p>}
          <div className="analysis-heading-meta">
            {!error && !noAnalysis && analysisDetail(analysis, language) && (
              <span className="analysis-chip">
                <Clock size={13} aria-hidden="true" />
                <span>{analysisDetail(analysis, language)}</span>
              </span>
            )}
            {!error && !noAnalysis && analysis?.status === "completed" && (
              <span className="analysis-chip chip-success">
                <CheckCircle2 size={13} aria-hidden="true" />
                <span>{copy.qualityVerified}</span>
              </span>
            )}
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
          <button className="secondary-button" type="button" onClick={() => {
            setError(""); setNoAnalysis(false); setAnalysis(null); setLoadAttempt((attempt) => attempt + 1);
          }}>
            {copy.retryLoad}
          </button>
        </div>
      )}

      {!analysis && !error && !noAnalysis && <div className="analysis-state-message" role="status">{copy.loading}</div>}

      {!error && !noAnalysis && analysis && (analysis.status === "queued" || analysis.status === "running") && (
        <div className="result-wait" role="status">{copy.processing}</div>
      )}

      {!error && !noAnalysis && analysis?.status === "rejected" && (
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

      {!error && !noAnalysis && analysis?.status === "failed" && (
        <div className="result-wait" role="alert">
          <h2>{copy.failedTitle}</h2>
          <p>{copy.failedBody}</p>
          <button className="primary-button" type="button" onClick={onNewAnalysis}>
            {copy.tryAgain} →
          </button>
        </div>
      )}

      {!error && !noAnalysis && analysis?.status === "completed" && <section hidden={view !== "products"} className="analysis-recommendation-section" aria-label={copy.recommendations}>
        <p className="recommendation-header-desc">{language === "th" ? "ใช้โปรไฟล์และผลิตภัณฑ์ที่ตรวจทานแล้ว ใช้ผลภาพเฉพาะเมื่อผ่านเกณฑ์" : "Based on your profile and reviewed products; image findings only when eligible."}</p>
        <RecommendationPanel language={language} />
      </section>}

      {!error && !noAnalysis && analysis?.status === "completed" && view === "results" && (
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
                        key={`${artifact}-${artifactAttempt}`}
                        className="analysis-result-image"
                        unoptimized
                        width={512}
                        height={512}
                        src={artifactSource}
                        alt={artifact === "overlay" ? copy.overlayAlt : copy.maskAlt}
                        onError={() => { setArtifactLoadError(true); setZoomOpen(false); }}
                      />
                      <span className="artifact-click-hint" aria-hidden="true">
                        <ZoomIn size={14} />
                        <span>{copy.clickToZoom}</span>
                      </span>
                    </>
                  ) : (
                    <div className="analysis-artifact-state">
                      <p role={artifactAvailability === "load-error" || artifactAvailability === "expired" ? "alert" : "status"}>
                        {artifactAvailability === "expired" && copy.expired}
                        {artifactAvailability === "unavailable" && copy.unavailable}
                        {artifactAvailability === "load-error" && copy.imageLoadError}
                      </p>
                      {artifactAvailability === "load-error" && (
                        <button className="secondary-button" type="button" onClick={() => {
                          setArtifactAttempt((attempt) => attempt + 1); setArtifactLoadError(false);
                        }}>{copy.retryImage}</button>
                      )}
                      <button className="secondary-button" type="button" onClick={onNewAnalysis}>{copy.retryAnalysis}</button>
                    </div>
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

                  <p className="analysis-caption">
                    <Info size={13} aria-hidden="true" className="caption-clock" />
                    <span>
                      {copy.overlayCaption}
                    </span>
                  </p>
                  {expiryLabel && <p className="analysis-caption">
                    <Lock size={13} aria-hidden="true" className="caption-clock" />
                    <span>{artifactAvailability === "expired" ? copy.artifactExpired : `${copy.expiryPrefix} ${expiryLabel} (${copy.thailandTime})`}</span>
                  </p>}
                </div>
              </section>

              {/* Right Column: Facial Metrics & Regional Breakdown */}
              <div className="analysis-results-column">
                {/* Hero Summary KPI Card */}
                <section className="analysis-summary" aria-labelledby="analysis-score-heading">
                  <div className="analysis-summary-header">
                    <div className="analysis-summary-title-wrap">
                      <h3 id="analysis-score-heading">{copy.overviewTitle}</h3>
                      <p className="analysis-overview-scope">{copy.overviewScope}</p>
                      <p className="analysis-summary-sub">{copy.markedAreaExplanation}</p>
                    </div>
                  </div>

                  <div className="analysis-summary-values">
                    <div className="analysis-kpi-tile analysis-coverage">
                      <div className="kpi-label-wrap">
                        <span className="kpi-label">{copy.markedArea}</span>
                        <span className="kpi-tag">{copy.percentageOfEvaluatedArea}</span>
                      </div>
                      <div className="kpi-number-wrap analysis-area-ring" style={{ background: `conic-gradient(var(--primary) ${Math.min(100, Math.max(0, score.overall.wrinkle_area_ratio * 100))}%, var(--primary-soft) 0)` }}>
                        <strong>{(score.overall.wrinkle_area_ratio * 100).toFixed(2)}%</strong>
                      </div>
                      <div className="kpi-mini-track" aria-hidden="true">
                        <span style={{ width: `${Math.min(100, Math.max(0, score.overall.wrinkle_area_ratio * 100))}%` }} />
                      </div>
                    </div>

                    <div className="analysis-kpi-tile analysis-total">
                      <div className="kpi-label-wrap">
                        <span className="kpi-label">{copy.experimentalScore}</span>
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
                  </div>

                  {evaluableRegions.length > 0 ? (
                    <div className="analysis-regional-overview">
                      <div className="analysis-region-data">
                        <dl className="analysis-region-facts">
                          <div><dt>{copy.markedArea}</dt><dd>{(score.overall.wrinkle_area_ratio * 100).toFixed(2)}<small>%</small></dd></div>
                          <div><dt>{copy.measuredRegions}</dt><dd>{evaluableRegions.length}<small> / {allRegions.length}</small></dd></div>
                          <div><dt>{copy.largestRegion}</dt><dd>{(primaryRegions[0][1].wrinkle_area_ratio * 100).toFixed(2)}<small>%</small></dd></div>
                        </dl>
                        <div className="analysis-regions analysis-regions-grid">
                        {primaryRegions.map(([name, value], index) => (
                          <RegionCard key={name} name={name} value={value} language={language} rank={index + 1} />
                        ))}
                        </div>
                      </div>
                      {analysis.result?.model_output?.personalized_outline_available && artifactAvailability === "available" && outlineError !== analysis.id ? (
                        <figure className="analysis-face-map">
                          {/* Authenticated generated SVG; never inline untrusted SVG markup. */}
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src="/api/analysis?artifact=outline" alt={copy.personalOutlineNote} onError={() => setOutlineError(analysis.id)} />
                          <figcaption><strong>{copy.mapTitle}</strong><span>{copy.personalOutlineNote}</span></figcaption>
                        </figure>
                      ) : <div>
                        {analysis.result?.model_output?.personalized_outline_available && <p className="analysis-section-intro">{copy.personalOutlineUnavailable}</p>}
                        <FaceRegionMap regions={evaluableRegions} language={language} />
                      </div>}
                    </div>
                  ) : (
                    <p className="analysis-section-intro">{analysis.result?.model_output?.regional_geometry_status === "unavailable" ? copy.noLandmarkRegions : copy.noRegionPixels}</p>
                  )}

                  <details className="analysis-extra-regions">
                    <summary><span>{copy.viewTechnicalData}</span><ChevronDown size={16} aria-hidden="true" /></summary>
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
                                  <small>{(value.wrinkle_area_ratio * 100).toFixed(2)}% · {copy.experimentalScore}: {value.score.toFixed(1)} / 100</small>
                                </>
                              ) : copy.noRegionPixels}
                            </dd>
                          </div>
                        ))}
                      </dl>

                      <div className="analysis-method-content">
                        <h4>{copy.method}</h4>
                        {score.roi_version && <p>ROI: <code>{score.roi_version}</code></p>}
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

            {/* Medical / Clinical Disclaimer */}
            <div className="analysis-disclaimer">
              <ShieldCheck size={22} aria-hidden="true" className="disclaimer-icon" />
              <div className="disclaimer-content">
                <strong>{copy.disclaimerTitle}</strong>
                <p>{copy.disclaimer}</p>
              </div>
            </div>

            {/* Lightbox / Zoom Modal for Desktop Inspection */}
            {zoomVisible && (
              <div
                className="analysis-zoom-modal"
                role="dialog"
                aria-modal="true"
                aria-label={copy.zoom}
                onClick={(e) => {
                  if (e.target === e.currentTarget) setZoomOpen(false);
                }}
              >
                <div className="analysis-zoom-dialog" ref={zoomDialogRef}>
                  <div className="analysis-zoom-header">
                    <div className="analysis-zoom-tabs" role="group" aria-label={copy.artifactControls}>
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
                        data-zoom-close
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
                        src={artifactSource}
                        onError={() => { setArtifactLoadError(true); setZoomOpen(false); }}
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
          </div>
        )
      )}
    </section>
  );
}
