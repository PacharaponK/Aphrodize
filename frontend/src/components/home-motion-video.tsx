"use client";

import { useEffect, useRef } from "react";

export default function HomeMotionVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let isNearViewport = !("IntersectionObserver" in window);
    const syncPlayback = () => {
      if (motionPreference.matches || !isNearViewport || document.visibilityState !== "visible") {
        video.pause();
        return;
      }

      void video.play().catch(() => undefined);
    };

    const observer = "IntersectionObserver" in window
      ? new IntersectionObserver(
          ([entry]) => {
            isNearViewport = entry.isIntersecting;
            syncPlayback();
          },
          { rootMargin: "120px 0px", threshold: 0 },
        )
      : null;
    observer?.observe(video);
    if (!observer) syncPlayback();
    motionPreference.addEventListener("change", syncPlayback);
    document.addEventListener("visibilitychange", syncPlayback);

    return () => {
      observer?.disconnect();
      motionPreference.removeEventListener("change", syncPlayback);
      document.removeEventListener("visibilitychange", syncPlayback);
      video.pause();
    };
  }, []);

  return (
    <video
      ref={videoRef}
      className="home-motion-video"
      muted
      loop
      playsInline
      preload="metadata"
      aria-hidden="true"
      tabIndex={-1}
    >
      <source src="/assets/aphrodize-home-background-118c8b84.mp4" type="video/mp4" />
    </video>
  );
}
