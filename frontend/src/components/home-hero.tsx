"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Camera } from "lucide-react";
import { useLanguage } from "./language-provider";

export function HomeHero() {
  const { language } = useLanguage();
  const th = language === "th";
  const hero = useRef<HTMLElement>(null);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reduced, setReduced] = useState(false);
  const phrase = th ? ["สวยในแบบคุณ", "ในทุกวัน"][index] : ["Young & Beautiful", "Day by day."][index];

  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (paused || reduced) return;
    let timer: ReturnType<typeof setTimeout>;
    const schedule = () => {
      clearTimeout(timer);
      if (!document.hidden) timer = setTimeout(() => { setIndex(value => (value + 1) % 2); schedule(); }, 4500);
    };
    schedule();
    document.addEventListener("visibilitychange", schedule);
    return () => { clearTimeout(timer); document.removeEventListener("visibilitychange", schedule); };
  }, [paused, reduced]);

  useEffect(() => {
    const element = hero.current;
    if (!element) return;
    const fine = matchMedia("(hover: hover) and (pointer: fine)");
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0, x = 0, y = 0, targetX = 0, targetY = 0;
    const paint = () => {
      x += (targetX - x) * .14; y += (targetY - y) * .14;
      element.style.setProperty("--face-x", `${x * 7}px`);
      element.style.setProperty("--face-y", `${y * 5}px`);
      element.style.setProperty("--scan-x", `${50 + x * 35}%`);
      element.style.setProperty("--scan-y", `${50 + y * 35}%`);
      frame = 0;
      if (Math.abs(targetX - x) + Math.abs(targetY - y) > .002) frame = requestAnimationFrame(paint);
    };
    const reset = () => {
      targetX = targetY = x = y = 0;
      cancelAnimationFrame(frame); frame = 0;
      element.classList.remove("is-tracking"); paint();
    };
    const move = (event: PointerEvent) => {
      if (!fine.matches || motion.matches || event.pointerType === "touch") return;
      const rect = element.getBoundingClientRect();
      targetX = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
      targetY = Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1));
      element.classList.add("is-tracking");
      if (!frame) frame = requestAnimationFrame(paint);
    };
    const visibility = () => { if (document.hidden) reset(); };
    element.addEventListener("pointermove", move, { passive: true });
    element.addEventListener("pointerleave", reset);
    element.addEventListener("pointercancel", reset);
    fine.addEventListener("change", reset); motion.addEventListener("change", reset);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      cancelAnimationFrame(frame);
      element.removeEventListener("pointermove", move); element.removeEventListener("pointerleave", reset);
      element.removeEventListener("pointercancel", reset); fine.removeEventListener("change", reset);
      motion.removeEventListener("change", reset); document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  let characterIndex = 0;
  return <section ref={hero} className="home-hero" aria-labelledby="home-hero-title">
    <div className="home-hero-background" aria-hidden="true">
      <Image src="/assets/aphrodize-hero-face.png" alt="" fill priority sizes="(max-width: 1600px) 100vw, 1600px" />
      <span className="home-hero-reticle" />
    </div>
    <div className="home-hero-copy">
      <p className="home-hero-eyebrow">{th ? "ภาพรวมประจำวันของคุณ" : "Your daily overview"}</p>
      <h1 id="home-hero-title">{th ? "รู้จักผิวของคุณ" : "Know your skin."}<span className={`home-hero-phrase${paused ? " is-paused" : ""}`}>
        <span className="home-hero-sr-only">{th ? "ในทุกวัน" : "Day by day."}</span>
        <span key={phrase} className="home-hero-words" aria-hidden="true">{phrase.split(" ").map((word, wordIndex) => <span className="home-hero-word" key={wordIndex}>{Array.from(word).map((letter, letterIndex) => <span className="home-hero-character" key={letterIndex} style={{ animationDelay: `${180 + characterIndex++ * 50}ms` }}>{letter}</span>)}</span>)}</span>
      </span></h1>
      <p className="home-hero-description">{th ? "ติดตามภาพผิวควบคู่กับพฤติกรรมการนอนและการดื่มน้ำ ผิว การนอน และการดื่มน้ำในมุมมองเดียว" : "Track your skin images alongside your sleep and hydration habits. Your skin, sleep and hydration in one place."}</p>
      <div className="home-hero-actions"><Link className="primary-button" href="/capture"><Camera size={20} aria-hidden="true" />{th ? "วิเคราะห์ผิว" : "Analyze skin"}<ArrowUpRight size={20} aria-hidden="true" /></Link><Link className="home-hero-secondary" href="#daily">{th ? "ภาพรวมประจำวัน" : "Your daily overview"}<ArrowUpRight size={20} aria-hidden="true" /></Link></div>
      <p className="home-hero-footnote">{th ? "เพื่อการติดตามส่วนบุคคล ไม่ใช่การวินิจฉัยทางการแพทย์" : "Personal tracking, not a medical diagnosis."}</p>
      {!reduced && <button type="button" className="home-hero-pause" aria-pressed={paused} onClick={() => setPaused(value => !value)}>{th ? (paused ? "เล่นข้อความเคลื่อนไหว" : "หยุดข้อความเคลื่อนไหว") : (paused ? "Resume text animation" : "Pause text animation")}</button>}
    </div>
    <p className="home-hero-media-label">{th ? "ภาพสาธิต ไม่ใช่ผลวิเคราะห์" : "Visual demo, not an analysis result"}</p>
  </section>;
}
