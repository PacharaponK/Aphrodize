"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

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
    <div className="simple-page">
      <main className="page-frame">
        <header className="page-header">
          <Link className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</Link>
          <nav className="page-nav"><Link href="/">ภาพรวม</Link><Link href="/capture">วิเคราะห์ภาพ</Link><Link href="/trend">แนวโน้ม</Link></nav>
        </header>
        <section className="page-content">
          <p className="eyebrow">IMAGE ANALYSIS</p>
          <h1>ผลวิเคราะห์ภาพ</h1>
          <p>คะแนนนี้เป็นค่าทดลองจากพื้นที่ที่โมเดลตรวจพบ ยังไม่ผ่านการตรวจสอบความแม่นยำหรือการรับรองทางคลินิก ไม่ใช่การวินิจฉัย</p>
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
                <div className="result-score"><p className="eyebrow">EXPERIMENTAL WRINKLE AREA SCORE</p><strong>{score.overall.score.toFixed(1)} <small>/ 100</small></strong><p>คะแนนทดลองที่ยังไม่ผ่านการตรวจสอบ · พื้นที่ตรวจพบ {(score.overall.wrinkle_area_ratio * 100).toFixed(2)}%</p></div>
              ) : <p role="status">ไม่มีคะแนนสำหรับภาพนี้</p>}
              <div className="detail-grid">
                <div>
                  <div className="artifact-tabs"><button type="button" className={artifact === "overlay" ? "active" : ""} onClick={() => { setArtifact("overlay"); setArtifactError(false); }}>ภาพซ้อน mask</button><button type="button" className={artifact === "mask" ? "active" : ""} onClick={() => { setArtifact("mask"); setArtifactError(false); }}>ภาพ mask</button></div>
                  <div className="overlay-card result-artifact">
                    {imagesAvailable && !artifactError ? (
                      <Image key={artifact} unoptimized width={512} height={512} src={`/api/analysis?artifact=${artifact}`} alt={artifact === "overlay" ? "ภาพใบหน้าที่ซ้อนตำแหน่ง mask ริ้วรอย" : "ภาพ mask พื้นที่ริ้วรอย"} onError={() => setArtifactError(true)} />
                    ) : <p>ภาพผลหมดอายุหรือไม่พร้อมใช้งาน กรุณาวิเคราะห์ภาพใหม่</p>}
                  </div>
                  {expiresAt && <p className="metadata">ภาพผลเป็น private และจะถูกลบภายใน 24 ชั่วโมงหลังประมวลผล</p>}
                </div>
                <div className="data-list">
                  {score && Object.entries(score.regions).map(([name, value]) => (
                    <div key={name}><strong>{REGIONS[name] ?? name}</strong><span>{value.score.toFixed(1)} / 100<br />พื้นที่ตรวจพบ {(value.wrinkle_area_ratio * 100).toFixed(2)}%</span></div>
                  ))}
                </div>
              </div>
              <p className="metadata">{score?.disclaimer} คำแนะนำจะไม่แสดงจนกว่า confidence calibration ผ่านเกณฑ์</p>
              <div className="page-actions"><Link className="primary-button" href="/capture">วิเคราะห์ภาพใหม่ →</Link><Link className="secondary-button" href="/">กลับหน้าภาพรวม</Link></div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
