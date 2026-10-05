"use client";

import { useEffect, useState } from "react";
import paths from "./brand-logo-paths.json";
import "./analysis-loader.css";

export function AnalysisLoader({ message, language }: { message: string; language: "en" | "th" }) {
  const [paused, setPaused] = useState(false);
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const update = () => setHidden(document.hidden);
    update();
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  const thai = language === "th";
  return <div className="analysis-logo-loader" data-paused={paused || hidden}>
    <svg className="analysis-loader-logo" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
      <g className="analysis-loader-track">{paths.map((d, i) => <path key={i} d={d} pathLength={360} />)}</g>
      <g className="analysis-loader-ink">{paths.map((d, i) => <path key={i} d={d} pathLength={360} />)}</g>
    </svg>
    <p className="analysis-loader-status" role="status" aria-live="polite">{message}</p>
    <p className="analysis-loader-note">{thai ? "ภาพเคลื่อนไหวแสดงสถานะรอ ไม่ใช่ความคืบหน้าหรือผลวิเคราะห์" : "This animation indicates waiting, not progress or analysis findings."}</p>
    <button className="secondary-button analysis-loader-pause" type="button" aria-pressed={paused} onClick={() => setPaused(!paused)}>
      {thai ? paused ? "เล่นภาพเคลื่อนไหว" : "หยุดภาพเคลื่อนไหว" : paused ? "Resume animation" : "Pause animation"}
    </button>
  </div>;
}
