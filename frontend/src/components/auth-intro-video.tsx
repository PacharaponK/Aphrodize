"use client";
import { useEffect, useRef } from "react";

export function AuthIntroVideo() {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const media = video.current;
    if (!media) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => {
      if (reduced.matches || document.hidden) media.pause();
      else void media.play().catch(() => { /* Static background when autoplay is unavailable. */ });
    };
    sync();
    reduced.addEventListener("change", sync);
    document.addEventListener("visibilitychange", sync);
    return () => { media.pause(); reduced.removeEventListener("change", sync); document.removeEventListener("visibilitychange", sync); };
  }, []);
  return (
    <div className="auth-intro-media" aria-hidden="true">
      <video ref={video} muted loop playsInline preload="metadata" tabIndex={-1}>
        <source src="/assets/aphrodize-auth-intro.mp4" type="video/mp4" />
      </video>
    </div>
  );
}
