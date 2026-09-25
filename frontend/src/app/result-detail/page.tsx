"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";

type AreaScore = { score: number; wrinkle_area_ratio: number };
type Score = { overall: AreaScore; regions: Record<string, AreaScore>; disclaimer: string };
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
  result: Result | null;
};

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

export default function ResultDetailPage() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [artifact, setArtifact] = useState<"overlay" | "mask">("overlay");
  const [artifactError, setArtifactError] = useState(false);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const response = await fetch("/api/analysis", { cache: "no-store" });
        if (!response.ok) {
          if (response.status === 401) throw new Error("ยังไม่มีผลวิเคราะห์ในเบราว์เซอร์นี้");
          const body = await response.json().catch(() => null);
          throw new Error(typeof body?.detail === "string" ? body.detail : "โหลดผลไม่สำเร็จ");
        }
        const next = (await response.json()) as Analysis;
        if (stopped) return;
        setAnalysis(next);
        if (next.status === "queued" || next.status === "running") {
          timer = setTimeout(poll, 2500);
        }
      } catch (reason) {
        if (!stopped) setError(reason instanceof Error ? reason.message : "โหลดผลไม่สำเร็จ");
      }
    }
    poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, []);

  const score = analysis?.result?.derived_score ?? analysis?.result?.experimental_score;
  const expiresAt = analysis?.result?.artifacts_expires_at;
  const imagesAvailable = Boolean(expiresAt);

  return (
    <WorkspaceShell active="capture" eyebrow="IMAGE ANALYSIS" title="ผลวิเคราะห์ภาพ" detail="ขั้นตอน 2 จาก 2 · ผลลัพธ์">
        <section className="page-content workspace-panel">
          <p className="eyebrow">EXPERIMENTAL RESULT</p>
          <h2>รายละเอียดผลวิเคราะห์</h2>
          <p>ดูพื้นที่ที่โมเดลตรวจพบในภาพ และคะแนนทดลองแยกตามบริเวณใบหน้า</p>
          {error && <div className="capture-error" role="alert">{error} <Link href="/capture">เริ่มวิเคราะห์ใหม่</Link></div>}
          {!analysis && !error && <p role="status">กำลังโหลดผล…</p>}
          {analysis && (analysis.status === "queued" || analysis.status === "running") && (
            <div className="result-wait" role="status">กำลังประมวลผลภาพ กรุณารอสักครู่…</div>
          )}
          {analysis?.status === "rejected" && (
            <div className="result-wait" role="alert"><h2>ภาพไม่ผ่านการตรวจคุณภาพ</h2><p>{analysis.quality_flags.join(", ") || "กรุณาลองภาพใหม่"}</p><Link className="primary-button" href="/capture">เลือกภาพใหม่ →</Link></div>
          )}
          {analysis?.status === "failed" && (
            <div className="result-wait" role="alert"><h2>ประมวลผลไม่สำเร็จ</h2><p>กรุณาลองอีกครั้งด้วยภาพใหม่</p><Link className="primary-button" href="/capture">ลองใหม่ →</Link></div>
          )}
          {analysis?.status === "completed" && (
            <>
              {score ? (
                <>
                  <div className="analysis-summary">
                    <div>
                      <p className="eyebrow">EXPERIMENTAL RESULT</p>
                      <h3>คะแนนพื้นที่ริ้วรอยรวม</h3>
                      <p>คะแนนทดลองจากพื้นที่ที่โมเดลตรวจพบ</p>
                    </div>
                    <div className="analysis-summary-values">
                      <div className="analysis-total"><strong>{score.overall.score.toFixed(1)}</strong><span>/ 100</span></div>
                      <div className="analysis-coverage"><span>พื้นที่ตรวจพบจริง</span><strong>{(score.overall.wrinkle_area_ratio * 100).toFixed(2)}%</strong></div>
                    </div>
                  </div>
                  <div className="analysis-detail-grid">
                    <section className="analysis-section" aria-labelledby="analysis-image-heading">
                      <div className="analysis-section-heading"><div><p className="eyebrow">VISUAL RESULT</p><h3 id="analysis-image-heading">ภาพผลวิเคราะห์</h3></div></div>
                      <div className="artifact-tabs" aria-label="เลือกรูปแบบภาพผลวิเคราะห์">
                        <button type="button" aria-pressed={artifact === "overlay"} className={artifact === "overlay" ? "active" : ""} onClick={() => { setArtifact("overlay"); setArtifactError(false); }}>ภาพซ้อนตำแหน่ง</button>
                        <button type="button" aria-pressed={artifact === "mask"} className={artifact === "mask" ? "active" : ""} onClick={() => { setArtifact("mask"); setArtifactError(false); }}>เฉพาะพื้นที่ตรวจพบ</button>
                      </div>
                      <div className="overlay-card result-artifact">
                        {imagesAvailable && !artifactError ? (
                          <Image key={artifact} unoptimized width={512} height={512} src={`/api/analysis?artifact=${artifact}`} alt={artifact === "overlay" ? "ภาพใบหน้าที่ซ้อนตำแหน่งพื้นที่ริ้วรอยที่ตรวจพบ" : "ภาพแสดงเฉพาะพื้นที่ริ้วรอยที่ตรวจพบ"} onError={() => setArtifactError(true)} />
                        ) : <p>ภาพผลหมดอายุหรือไม่พร้อมใช้งาน กรุณาวิเคราะห์ภาพใหม่</p>}
                      </div>
                      <p className="analysis-caption">สีบนภาพแสดงตำแหน่งที่โมเดลตรวจพบ{expiresAt && " · ภาพเป็นส่วนตัวและจะถูกลบภายใน 24 ชั่วโมง"}</p>
                    </section>
                    <section className="analysis-section" aria-labelledby="analysis-regions-heading">
                      <div className="analysis-section-heading"><div><p className="eyebrow">BY REGION</p><h3 id="analysis-regions-heading">คะแนนรายบริเวณ</h3></div><span>{Object.keys(score.regions).length} บริเวณ</span></div>
                      <p className="analysis-section-intro">คะแนน 0–100 เป็นค่าที่ขยายจากสัดส่วนพื้นที่ตรวจพบ ดูเปอร์เซ็นต์จริงของแต่ละบริเวณประกอบ</p>
                      <div className="analysis-regions">
                        {Object.entries(score.regions).map(([name, value]) => (
                          <div className="analysis-region" key={name}>
                            <div className="analysis-region-top"><strong>{REGIONS[name] ?? name}</strong><span><b>{value.score.toFixed(1)}</b> / 100</span></div>
                            <div className="analysis-region-track" aria-hidden="true"><span style={{ width: `${value.score}%` }} /></div>
                            <p>พื้นที่ตรวจพบจริง <strong>{(value.wrinkle_area_ratio * 100).toFixed(2)}%</strong></p>
                          </div>
                        ))}
                      </div>
                    </section>
                  </div>
                  <div className="analysis-disclaimer"><strong>เกี่ยวกับผลนี้</strong><p>คะแนนนี้เป็นการวัดจากภาพเพื่อการทดลอง ยังไม่ผ่านการตรวจสอบความแม่นยำหรือการรับรองทางคลินิก ไม่ใช่การวินิจฉัยหรือหลักฐานว่าการรักษาใดจะได้ผล</p></div>
                </>
              ) : <div className="result-wait" role="status">ไม่มีคะแนนสำหรับภาพนี้</div>}
              <div className="page-actions"><Link className="primary-button" href="/capture">วิเคราะห์ภาพใหม่ →</Link><Link className="secondary-button" href="/">กลับหน้าภาพรวม</Link></div>
            </>
          )}
        </section>
    </WorkspaceShell>
  );
}
