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

      const resultCards = gsap.utils.toArray<HTMLElement>(
        ".home-result-detail-list .result-card",
        dashboard,
      );
      resultCards.forEach((card, index) => {
        gsap.fromTo(
          card,
          { y: 26 + index * 8, autoAlpha: 0.55, scale: 0.985 },
          {
            y: 0,
            autoAlpha: 1,
            scale: 1,
            ease: "none",
            scrollTrigger: {
              trigger: card,
              start: "top 88%",
              end: "top 58%",
              scrub: 0.5,
              invalidateOnRefresh: true,
            },
          },
        );
      });

      const revealTargets = gsap.utils.toArray<HTMLElement>(
        "[data-scroll-reveal]",
        dashboard,
      );
      revealTargets.forEach((target) => {
        gsap.fromTo(
          target,
          { y: 24, autoAlpha: 0.65 },
          {
            y: 0,
            autoAlpha: 1,
            duration: 0.7,
            ease: "power2.out",
            scrollTrigger: {
              trigger: target,
              start: "top 88%",
              toggleActions: "play none none reverse",
              invalidateOnRefresh: true,
            },
          },
        );
      });

      const score = dashboard.querySelector<HTMLElement>(".home-overview-score");
      if (score) {
        gsap.fromTo(
          score,
          { y: 18 },
          {
            y: 0,
            ease: "none",
            scrollTrigger: {
              trigger: score,
              start: "top 92%",
              end: "top 62%",
              scrub: 0.5,
              invalidateOnRefresh: true,
            },
          },
        );
      }
    });

    return () => media.revert();
  }, []);

  return null;
}
