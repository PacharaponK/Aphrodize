"use client";

import { useEffect } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

export function HomeScrollMotion() {
  useEffect(() => {
    const dashboard = document.querySelector<HTMLElement>("#dashboard");
    if (!dashboard) return;

    gsap.registerPlugin(ScrollTrigger);

    const media = gsap.matchMedia(dashboard);
    media.add("(prefers-reduced-motion: no-preference)", () => {
      const mediaFrame = dashboard.querySelector<HTMLElement>(".home-motion-frame");
      const backgroundVideo = mediaFrame?.querySelector<HTMLElement>(".home-motion-video");
      if (mediaFrame && backgroundVideo) {
        gsap.fromTo(
          backgroundVideo,
          { yPercent: 3, scale: 1.07 },
          {
            yPercent: -3,
            scale: 1.07,
            ease: "none",
            scrollTrigger: {
              trigger: mediaFrame,
              start: "top bottom",
              end: "bottom top",
              scrub: 0.7,
              invalidateOnRefresh: true,
            },
          },
        );
      }

      const cards = gsap.utils.toArray<HTMLElement>(
        ".home-topbar, .home-overview-card, .home-wellness-card, .home-action-card, .home-metric-card, .home-insights-card",
        dashboard,
      );
      cards.forEach((card, index) => {
        gsap.fromTo(
          card,
          {
            x: card.matches(".home-overview-card") ? -40 : card.matches(".home-wellness-card") ? 40 : 0,
            y: 44,
            scale: 0.96,
            opacity: 0.2,
          },
          {
            x: 0,
            y: 0,
            scale: 1,
            opacity: 1,
            duration: 0.85,
            delay: Math.min(index * 0.1, 0.3),
            ease: "power3.out",
            scrollTrigger: {
              trigger: card,
              start: "top 92%",
              toggleActions: "restart none restart reverse",
            },
          },
        );
      });
    });

    return () => media.revert();
  }, []);

  return null;
}
