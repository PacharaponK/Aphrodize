"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { RecommendationPanel } from "@/app/recommendation/recommendation-panel";
import { WorkspaceShell } from "@/components/workspace-shell";

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

const REGIONS: Record<string, string> = {
  forehead: "หน้าผาก",
  glabella: "ระหว่างคิ้ว",
  image_left_periocular: "รอบดวงตาซ้ายของภาพ",
  image_right_periocular: "รอบดวงตาขวาของภาพ",
  image_left_cheek: "แก้มซ้ายของภาพ",
  image_right_cheek: "แก้มขวาของภาพ",
  nasolabial: "ร่องแก้ม",
  perioral: "รอบปาก",
};

const QUALITY_FLAG_COPY: Record<string, string> = {
  unreadable_image: "ระบบเปิดอ่านไฟล์ภาพนี้ไม่ได้",
  resolution_too_low: "ภาพมีความละเอียดไม่เพียงพอสำหรับการประเมิน",
  no_face_detected: "ระบบหาใบหน้าในภาพไม่พบ",
  multiple_faces_detected: "พบหลายใบหน้า กรุณาใช้ภาพที่มีใบหน้าคนเดียว",
  face_too_small_pixels: "ใบหน้าอยู่ไกลหรือมีขนาดเล็กเกินไปในภาพ",
  face_too_small_ratio: "กรุณาถ่ายให้ใบหน้าอยู่ใกล้และมีขนาดใหญ่ขึ้นในภาพ",
  landmark_confidence_too_low: "ระบบระบุตำแหน่งใบหน้าได้ไม่ชัดเจน",
  exposure_too_dark: "ภาพมืดเกินไป กรุณาถ่ายในบริเวณที่มีแสงเพียงพอ",
  exposure_too_bright: "ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงจ้าที่ใบหน้า",
  dark_clipping_excessive: "รายละเอียดในภาพมืดเกินกว่าจะประเมินได้",
  bright_clipping_excessive: "แสงจ้าทำให้รายละเอียดใบหน้าบางส่วนหายไป",
  image_too_blurry: "ภาพไม่คมชัด กรุณาถือกล้องให้นิ่งแล้วถ่ายใหม่",
  pose_roll_excessive: "กรุณาจัดศีรษะให้ตรงกับกล้อง",
  pose_yaw_excessive: "กรุณาหันหน้าเข้าหากล้องโดยตรง",
  pose_pitch_excessive: "กรุณามองตรงและจัดกล้องให้อยู่ระดับใบหน้า",
  invalid_face_bounds: "ระบบระบุขอบเขตใบหน้าได้ไม่ครบถ้วน",
  face_parsing_area_too_small: "พื้นที่ใบหน้าที่ระบบระบุมีขนาดเล็กเกินไป",
  face_parsing_area_too_large: "ระบบแยกพื้นที่ใบหน้าออกจากภาพได้ไม่ชัดเจน",
};

function getArtifactAvailability(expiresAt?: string, expiryTick = 0): ArtifactAvailability {
  if (!expiresAt) return "unavailable";
  const expiration = Date.parse(expiresAt);
  if (!Number.isFinite(expiration)) return "unavailable";
  return expiration <= Date.now() || expiryTick >= expiration ? "expired" : "available";
}

function formatArtifactExpiry(expiresAt: string): string | null {
  const timestamp = Date.parse(expiresAt);
  if (!Number.isFinite(timestamp)) return null;
  return new Intl.DateTimeFormat("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(timestamp);
}

function formatAnalysisDate(createdAt?: string): string | null {
  if (!createdAt) return null;
  const timestamp = Date.parse(createdAt);
  if (!Number.isFinite(timestamp)) return null;
  return new Intl.DateTimeFormat("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(timestamp);
}

function analysisDetail(analysis: Analysis | null): string | undefined {
  if (!analysis) return undefined;
  const date = formatAnalysisDate(analysis.created_at);
  if (analysis.status === "queued" || analysis.status === "running") {
    return [analysis.status === "queued" ? "รอประมวลผล" : "กำลังประมวลผล", date].filter(Boolean).join(" · ");
  }
  return date ? `วิเคราะห์เมื่อ ${date}` : undefined;
}

function qualityFlagLabel(flag: string): string {
  return QUALITY_FLAG_COPY[flag] ?? "รูปภาพไม่ผ่านเงื่อนไขคุณภาพที่ระบบใช้ประเมิน";
}

export default function ResultDetailPage() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [noAnalysis, setNoAnalysis] = useState(false);
  const [artifact, setArtifact] = useState<"overlay" | "mask">("overlay");
  const [artifactLoadError, setArtifactLoadError] = useState(false);
  const [expiryTick, setExpiryTick] = useState(0);

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
          throw new Error("ไม่สามารถโหลดผลวิเคราะห์ได้ในขณะนี้");
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
        if (!stopped) setError("ไม่สามารถโหลดผลวิเคราะห์ได้ในขณะนี้ กรุณาลองอีกครั้ง");
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
  const expiryLabel = expiresAt ? formatArtifactExpiry(expiresAt) : null;

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

  const currentArtifactAvailability = getArtifactAvailability(expiresAt, expiryTick);
  const artifactAvailability: ArtifactAvailability = currentArtifactAvailability === "available" && artifactLoadError
    ? "load-error"
    : currentArtifactAvailability;

  return (
    <WorkspaceShell active="capture" eyebrow="FACE ANALYSIS" title="ผลวิเคราะห์ใบหน้า" detail={analysisDetail(analysis)}>
      <section className="page-content workspace-panel analysis-page">
        <div className="analysis-page-heading">
          <div>
            <p className="eyebrow">EXPERIMENTAL RESULT</p>
            <h2>ผลจากภาพที่ส่งวิเคราะห์</h2>
            <p>แสดงเฉพาะค่าที่ระบบประเมินได้จากภาพนี้ คะแนนเป็นการวัดเชิงทดลอง ไม่ใช่การวินิจฉัย</p>
          </div>
          <nav className="analysis-page-actions" aria-label="การดำเนินการกับผลวิเคราะห์">
            <Link className="primary-button" href="/capture">วิเคราะห์ภาพใหม่ →</Link>
            <Link className="secondary-button" href="/">กลับหน้าภาพรวม</Link>
          </nav>
        </div>
        {/* Render one status-specific message while the analysis is not complete. */}
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
              <p className="eyebrow">NO ANALYSIS YET</p>
              <h3>ยังไม่มีผลวิเคราะห์ในเบราว์เซอร์นี้</h3>
              <p>เริ่มจากส่งภาพใบหน้าที่หน้า “วิเคราะห์” เมื่อระบบประมวลผลเสร็จ ผลจริงจะแสดงที่หน้านี้</p>
            </div>
          </div>
        )}
        {error && <div className="analysis-state-message" role="alert"><h3>โหลดผลวิเคราะห์ไม่สำเร็จ</h3><p>{error}</p><button className="secondary-button" type="button" onClick={() => window.location.reload()}>ลองโหลดอีกครั้ง</button></div>}
        {!analysis && !error && !noAnalysis && <div className="analysis-state-message" role="status">กำลังโหลดผลวิเคราะห์…</div>}
        {analysis && (analysis.status === "queued" || analysis.status === "running") && (
          <div className="result-wait" role="status">กำลังประมวลผลภาพ กรุณารอสักครู่…</div>
        )}
        {analysis?.status === "rejected" && (
          <div className="result-wait" role="alert">
            <h2>ภาพไม่ผ่านการตรวจคุณภาพ</h2>
            {analysis.quality_flags.length ? (
              <ul className="quality-flag-list">
                {[...new Set(analysis.quality_flags)].map((flag) => <li key={flag}>{qualityFlagLabel(flag)}</li>)}
              </ul>
            ) : <p>กรุณาลองถ่ายภาพใหม่ โดยจัดใบหน้าให้ชัดและหันตรงเข้าหากล้อง</p>}
            <Link className="primary-button" href="/capture">เลือกภาพใหม่ →</Link>
          </div>
        )}
        {analysis?.status === "failed" && (
          <div className="result-wait" role="alert"><h2>ประมวลผลไม่สำเร็จ</h2><p>กรุณาลองอีกครั้งด้วยภาพใหม่</p><Link className="primary-button" href="/capture">ลองใหม่ →</Link></div>
        )}
        {/* A completed inference can still contain an experimental, abstained score. */}
        {analysis?.status === "completed" && (
          <>
            {score && hasScorableOverall ? (
              <>
                <div className="analysis-result-grid">
                  <section className="analysis-section analysis-image-section" aria-labelledby="analysis-image-heading">
                    <div className="analysis-section-heading">
                      <div><p className="eyebrow">VISUAL RESULT</p><h3 id="analysis-image-heading">ภาพผลวิเคราะห์</h3></div>
                    </div>
                    <div className="artifact-tabs" role="group" aria-label="เลือกรูปแบบภาพผลวิเคราะห์">
                      {/* Switch only the displayed artifact; no new inference runs here. */}
                      <button type="button" aria-pressed={artifact === "overlay"} className={artifact === "overlay" ? "active" : ""} onClick={() => { setArtifact("overlay"); setArtifactLoadError(false); }}>ภาพซ้อนตำแหน่ง</button>
                      <button type="button" aria-pressed={artifact === "mask"} className={artifact === "mask" ? "active" : ""} onClick={() => { setArtifact("mask"); setArtifactLoadError(false); }}>เฉพาะพื้นที่ตรวจพบ</button>
                    </div>
                    <div className="overlay-card result-artifact" aria-live="polite">
                      {artifactAvailability === "available" ? (
                        <Image
                          key={artifact}
                          className="analysis-result-image"
                          unoptimized
                          width={512}
                          height={512}
                          src={`/api/analysis?artifact=${artifact}`}
                          alt={artifact === "overlay" ? "ภาพใบหน้าที่ซ้อนตำแหน่งพื้นที่ริ้วรอยที่ตรวจพบ" : "ภาพแสดงเฉพาะพื้นที่ริ้วรอยที่ตรวจพบ"}
                          onError={() => setArtifactLoadError(true)}
                        />
                      ) : (
                        <p role={artifactAvailability === "load-error" || artifactAvailability === "expired" ? "alert" : "status"}>
                          {artifactAvailability === "expired" && "ภาพผลวิเคราะห์หมดอายุแล้ว กรุณาวิเคราะห์ภาพใหม่เพื่อดูภาพประกอบ"}
                          {artifactAvailability === "unavailable" && "ไม่มีภาพผลวิเคราะห์ที่เปิดดูได้ กรุณาวิเคราะห์ภาพใหม่"}
                          {artifactAvailability === "load-error" && "โหลดภาพผลวิเคราะห์ไม่สำเร็จ กรุณาลองอีกครั้งหรือวิเคราะห์ภาพใหม่"}
                        </p>
                      )}
                    </div>
                    <p className="analysis-caption">
                      สีบนภาพแสดงตำแหน่งที่โมเดลทำเครื่องหมาย
                      {artifactAvailability === "available" && expiryLabel && ` · ภาพส่วนตัวเปิดดูได้ถึง ${expiryLabel} น. (เวลาไทย)`}
                      {artifactAvailability === "expired" && " · ภาพหมดอายุการเข้าถึงแล้ว"}
                    </p>
                  </section>

                  <div className="analysis-results-column">
                    <section className="analysis-summary" aria-labelledby="analysis-score-heading">
                      <div className="analysis-summary-copy">
                        <p className="eyebrow">EXPERIMENTAL SCORE</p>
                        <h3 id="analysis-score-heading">คะแนนพื้นที่ที่โมเดลทำเครื่องหมาย</h3>
                        <p>คะแนน 0–100 คำนวณจากสัดส่วนพื้นที่ที่โมเดลทำเครื่องหมายและมีเพดาน 100; คะแนนที่สูงขึ้นหมายถึงสัดส่วนตามสูตรสูงขึ้น ไม่ใช่คะแนนสุขภาพผิวหรือการวินิจฉัย หากถึงเพดานให้ดูเปอร์เซ็นต์จริงประกอบ</p>
                      </div>
                      <div className="analysis-summary-values">
                        <div className="analysis-total"><strong>{score.overall.score.toFixed(1)}</strong><span>/ 100</span></div>
                        <div className="analysis-coverage"><span>สัดส่วนพื้นที่ที่ทำเครื่องหมาย</span><strong>{(score.overall.wrinkle_area_ratio * 100).toFixed(2)}%</strong></div>
                      </div>
                    </section>

                    <section className="analysis-section analysis-region-section" aria-labelledby="analysis-regions-heading">
                      <div className="analysis-section-heading">
                        <div><p className="eyebrow">BY REGION</p><h3 id="analysis-regions-heading">คะแนนแยกตามบริเวณ</h3></div>
                        <span>{evaluableRegions.length} จาก {allRegions.length} บริเวณที่ประเมินได้</span>
                      </div>
                      <p className="analysis-section-intro">ค่าคะแนนและสัดส่วนพื้นที่เป็นผลจากภาพ ไม่ใช่ระดับความรุนแรงหรือความเสี่ยงทางสุขภาพ</p>
                      {displayedRegions.length ? (
                        <div className="analysis-regions">
                          {displayedRegions.map(([name, value]) => {
                            if (value.evaluated_pixels <= 0) {
                              return (
                                <div className="analysis-region analysis-region-unscorable" key={name}>
                                  <div className="analysis-region-top"><strong>{REGIONS[name] ?? name}</strong><span>ประเมินไม่ได้</span></div>
                                  <p>ไม่มีพิกเซลเพียงพอสำหรับคำนวณ</p>
                                </div>
                              );
                            }
                            const areaPercent = value.wrinkle_area_ratio * 100;
                            return (
                              <div className="analysis-region" key={name}>
                                <div className="analysis-region-top">
                                  <strong>{REGIONS[name] ?? name}</strong>
                                  <span><b>{value.score.toFixed(1)}</b> / 100</span>
                                </div>
                                <div className="analysis-region-track" role="progressbar" aria-label={`สัดส่วนพื้นที่ทำเครื่องหมาย: ${REGIONS[name] ?? name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, Math.max(0, areaPercent))} aria-valuetext={`${areaPercent.toFixed(2)}% ของพื้นที่ที่ประเมินได้`}><span style={{ width: `${Math.min(100, Math.max(0, areaPercent))}%` }} /></div>
                                <p>พื้นที่ทำเครื่องหมาย <strong>{areaPercent.toFixed(2)}%</strong><span className="analysis-region-pixels">{value.wrinkle_pixels.toLocaleString()} / {value.evaluated_pixels.toLocaleString()} พิกเซล</span></p>
                              </div>
                            );
                          })}
                        </div>
                      ) : <p className="analysis-section-intro">ไม่มีบริเวณที่มีพิกเซลเพียงพอสำหรับคำนวณ</p>}
                    </section>

                    <details className="analysis-method">
                      <summary>วิธีคำนวณคะแนน</summary>
                      <div className="analysis-method-content">
                        <p>สัดส่วนพื้นที่ทำเครื่องหมาย = พิกเซลที่โมเดลทำเครื่องหมาย ÷ พิกเซลที่ใช้ประเมินได้</p>
                        <p>สูตรคะแนน 0–100 = <code>{score.formula}</code> โดยใช้สัดส่วนแบบทศนิยม (1% = 0.01)</p>
                        <p>ภาพนี้: {score.overall.wrinkle_pixels.toLocaleString()} ÷ {score.overall.evaluated_pixels.toLocaleString()} พิกเซล = {(score.overall.wrinkle_area_ratio * 100).toFixed(2)}% และได้คะแนน {score.overall.score.toFixed(1)} / 100</p>
                        <p>คะแนนมีเพดานที่ 100 จึงควรดูสัดส่วนเปอร์เซ็นต์จริงประกอบ คะแนนนี้ไม่ยืนยันว่ามีหรือไม่มีริ้วรอยจริง</p>
                      </div>
                    </details>

                    {analysis.result?.recommendation_gate?.eligible === true && (
                      <section className="analysis-section analysis-recommendation-section" aria-labelledby="analysis-recommendations-heading">
                        <div className="analysis-section-heading">
                          <div><p className="eyebrow">PERSONAL GUIDANCE</p><h3 id="analysis-recommendations-heading">คำแนะนำที่ผ่านเกณฑ์</h3></div>
                        </div>
                        <RecommendationPanel />
                      </section>
                    )}
                  </div>
                </div>
                <div className="analysis-disclaimer"><strong>ข้อควรรู้</strong><p>ผลนี้เป็นการวัดเชิงทดลองจากภาพ ไม่ใช่การวินิจฉัยหรือการประเมินสุขภาพผิว และยังไม่ได้รับการรับรองทางคลินิก</p></div>
              </>
            ) : <div className="result-wait" role="status">ไม่มีคะแนนสำหรับภาพนี้</div>}
          </>
        )}
      </section>
    </WorkspaceShell>
  );
}
