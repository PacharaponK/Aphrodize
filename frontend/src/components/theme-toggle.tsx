"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useLanguage } from "./language-provider";

type ThemeApi = {
  setTheme: (theme: "black" | "pastel") => void;
  current: () => string;
};

declare global {
  interface Window {
    AphrodizeTheme?: ThemeApi;
  }
}

export function useTheme() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const syncTheme = () => setIsDark(document.documentElement.dataset.theme === "black");
    syncTheme();
    window.addEventListener("aphrodize-theme-change", syncTheme);
    window.addEventListener("storage", syncTheme);
    return () => {
      window.removeEventListener("aphrodize-theme-change", syncTheme);
      window.removeEventListener("storage", syncTheme);
    };
  }, []);

  const setTheme = (nextTheme: "black" | "pastel") => {
    const themeApi = typeof window !== "undefined" ? window.AphrodizeTheme : undefined;
    if (themeApi) {
      themeApi.setTheme(nextTheme);
    } else if (typeof document !== "undefined") {
      const root = document.documentElement;
      root.dataset.theme = nextTheme;
      root.classList.toggle("dark", nextTheme === "black");
      root.style.colorScheme = nextTheme === "black" ? "dark" : "light";
      try {
        window.localStorage?.setItem("aphrodize-theme", nextTheme);
      } catch {
        // Storage unavailable
      }
      window.dispatchEvent(new Event("aphrodize-theme-change"));
    }
    setIsDark(nextTheme === "black");
  };

  const toggleTheme = () => setTheme(isDark ? "pastel" : "black");

  return {
    isDark,
    theme: isDark ? "black" : ("pastel" as const),
    setTheme,
    toggleTheme,
  };
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { isDark, toggleTheme } = useTheme();
  const { language } = useLanguage();

  const label = language === "en"
    ? isDark ? "Switch to light theme" : "Switch to dark theme"
    : isDark ? "เปลี่ยนเป็นธีมสว่าง" : "เปลี่ยนเป็นธีมมืด";

  return (
    <button
      className={`theme-toggle ${className}`.trim()}
      type="button"
      aria-label={label}
      aria-pressed={isDark}
      title={label}
      onClick={toggleTheme}
    >
      {isDark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
      <span>{language === "en" ? isDark ? "Light" : "Dark" : isDark ? "สว่าง" : "มืด"}</span>
    </button>
  );
}

