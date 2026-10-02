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
              scrub: 1.2,
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
            y: 28,
            scale: 0.985,
            opacity: 0.35,
          },
          {
            x: 0,
            y: 0,
            scale: 1,
            opacity: 1,
            duration: 0.8,
            delay: Math.min(index * 0.06, 0.18),
            ease: "power2.out",
            force3D: true,
            scrollTrigger: {
              trigger: card,
              start: "top 92%",
              toggleActions: "play none none none",
              fastScrollEnd: true,
              preventOverlaps: true,
            },
          },
        );
      });
    });

    return () => media.revert();
  }, []);

  return null;
}
