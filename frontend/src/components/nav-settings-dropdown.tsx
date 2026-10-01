"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Globe, Moon, Settings, Sun } from "lucide-react";
import { useLanguage } from "./language-provider";
import { useTheme } from "./theme-toggle";

export function NavSettingsDropdown({
  showTheme = true,
  className = "",
}: {
  showTheme?: boolean;
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { language, setLanguage } = useLanguage();
  const { isDark, setTheme } = useTheme();

  // Close when pressing Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Close when clicking outside of the dropdown container
  useEffect(() => {
    if (!isOpen) return;
    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [isOpen]);

  const settingsLabel = language === "en" ? "Settings" : "การตั้งค่า";
  const languageLabel = language === "en" ? "Language" : "ภาษา";
  const themeLabel = language === "en" ? "Theme" : "ธีม";
  const lightLabel = language === "en" ? "Light" : "สว่าง";
  const darkLabel = language === "en" ? "Dark" : "มืด";

  return (
    <div ref={containerRef} className={`app-nav-settings ${className}`.trim()}>
      <button
        ref={triggerRef}
        type="button"
        className={`app-nav-settings-trigger${isOpen ? " is-open" : ""}`}
        aria-label={settingsLabel}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-controls="nav-settings-dropdown"
        title={settingsLabel}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <Settings size={18} className="app-nav-settings-icon" aria-hidden="true" />
      </button>

      <div
        id="nav-settings-dropdown"
        className={`app-nav-settings-dropdown${isOpen ? " is-open" : ""}`}
        role="region"
        aria-label={settingsLabel}
        hidden={!isOpen}
      >
        <div className="app-nav-settings-header">
          <span className="app-nav-settings-heading">{settingsLabel}</span>
        </div>

        {/* Language setting */}
        <div className="app-nav-settings-group">
          <div className="app-nav-settings-group-header">
            <Globe size={14} aria-hidden="true" />
            <span>{languageLabel}</span>
          </div>
          <div
            className="app-nav-settings-segmented"
            role="radiogroup"
            aria-label={language === "en" ? "Select language" : "เลือกภาษา"}
          >
            <button
              type="button"
              role="radio"
              aria-checked={language === "th"}
              aria-label="เปลี่ยนภาษาเป็นไทย"
              className={`app-nav-settings-option${language === "th" ? " active" : ""}`}
              onClick={() => setLanguage("th")}
            >
              <span>ไทย</span>
              {language === "th" && <Check size={13} className="app-nav-settings-check" aria-hidden="true" />}
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={language === "en"}
              aria-label="Switch language to English"
              className={`app-nav-settings-option${language === "en" ? " active" : ""}`}
              onClick={() => setLanguage("en")}
            >
              <span>English</span>
              {language === "en" && <Check size={13} className="app-nav-settings-check" aria-hidden="true" />}
            </button>
          </div>
        </div>

        {/* Theme setting */}
        {showTheme && (
          <div className="app-nav-settings-group">
            <div className="app-nav-settings-group-header">
              <Sun size={14} aria-hidden="true" />
              <span>{themeLabel}</span>
            </div>
            <div
              className="app-nav-settings-segmented"
              role="radiogroup"
              aria-label={language === "en" ? "Select theme" : "เลือกธีม"}
            >
              <button
                type="button"
                role="radio"
                aria-checked={!isDark}
                aria-label="Switch to light theme"
                className={`app-nav-settings-option${!isDark ? " active" : ""}`}
                onClick={() => setTheme("pastel")}
              >
                <Sun size={14} aria-hidden="true" />
                <span>{lightLabel}</span>
                {!isDark && <Check size={13} className="app-nav-settings-check" aria-hidden="true" />}
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={isDark}
                aria-label="Switch to dark theme"
                className={`app-nav-settings-option${isDark ? " active" : ""}`}
                onClick={() => setTheme("black")}
              >
                <Moon size={14} aria-hidden="true" />
                <span>{darkLabel}</span>
                {isDark && <Check size={13} className="app-nav-settings-check" aria-hidden="true" />}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
