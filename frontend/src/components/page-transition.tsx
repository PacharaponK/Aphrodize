"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";

/** Entry-only polish: routing, child state, focus and scroll stay owned by Next. */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const previousPath = useRef(pathname);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (previousPath.current === pathname) return;
    previousPath.current = pathname;

    const main = container.current?.querySelector("main");
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!main || preference.matches || document.hidden || typeof main.animate !== "function") return;

    // Never transform a route ancestor: fixed/dialog/UV geometry must stay stable.
    // No fill mode or CSS hidden state, so interruption always restores normal content.
    const animation = main.animate(
      [{ opacity: pathname === "/" ? 0.9 : 0.96 }, { opacity: 1 }],
      { duration: pathname === "/" ? 240 : 160, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
    );
    const stop = () => {
      if (preference.matches || document.hidden) animation.cancel();
    };
    preference.addEventListener("change", stop);
    document.addEventListener("visibilitychange", stop);

    return () => {
      animation.cancel();
      preference.removeEventListener("change", stop);
      document.removeEventListener("visibilitychange", stop);
    };
  }, [pathname]);

  // A layout-neutral boundary, not a keyed template that resets forms on navigation.
  return <div ref={container} style={{ display: "contents" }}>{children}</div>;
}
