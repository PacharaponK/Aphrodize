"use client";

import { createContext, useCallback, useContext, useEffect, useSyncExternalStore, type ReactNode } from "react";

export type Language = "th" | "en";

type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);
const STORAGE_KEY = "aphrodize-language";
const languageSubscribers = new Set<() => void>();
let languageSnapshot: Language = "en";
let hasReadStoredLanguage = false;

function notifyLanguageSubscribers() {
  languageSubscribers.forEach((subscriber) => subscriber());
}

function subscribeToLanguage(onChange: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key !== STORAGE_KEY) return;
    languageSnapshot = event.newValue === "th" ? "th" : "en";
    hasReadStoredLanguage = true;
    notifyLanguageSubscribers();
  };
  languageSubscribers.add(onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    languageSubscribers.delete(onChange);
    window.removeEventListener("storage", onStorage);
  };
}

function getLanguageSnapshot(): Language {
  if (!hasReadStoredLanguage && typeof window !== "undefined") {
    hasReadStoredLanguage = true;
    try {
      languageSnapshot = window.localStorage?.getItem(STORAGE_KEY) === "th" ? "th" : "en";
    } catch {
      languageSnapshot = "en";
    }
  }
  return languageSnapshot;
}

function getServerLanguageSnapshot(): Language {
  return "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const language = useSyncExternalStore(subscribeToLanguage, getLanguageSnapshot, getServerLanguageSnapshot);

  const setLanguage = useCallback((nextLanguage: Language) => {
    languageSnapshot = nextLanguage;
    hasReadStoredLanguage = true;
    try {
      window.localStorage?.setItem(STORAGE_KEY, nextLanguage);
    } catch {
      // Keep the in-memory preference working when browser storage is unavailable.
    }
    notifyLanguageSubscribers();
    window.dispatchEvent(new Event("aphrodize-language-change"));
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
  }, [language]);

  return <LanguageContext.Provider value={{ language, setLanguage }}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used within LanguageProvider");
  return context;
}

export function LanguageToggle({ className = "" }: { className?: string }) {
  const { language, setLanguage } = useLanguage();
  const nextLanguage: Language = language === "en" ? "th" : "en";

  return (
    <button
      className={`language-toggle${className ? ` ${className}` : ""}`}
      type="button"
      aria-label={language === "en" ? "เปลี่ยนภาษาเป็นไทย" : "Switch language to English"}
      title={language === "en" ? "เปลี่ยนภาษาเป็นไทย" : "Switch language to English"}
      onClick={() => setLanguage(nextLanguage)}
    >
      {nextLanguage === "th" ? "ไทย" : "EN"}
    </button>
  );
}

export function LocalizedText({ th, en }: { th: string; en: string }) {
  const { language } = useLanguage();
  return <span lang={language}>{language === "en" ? en : th}</span>;
}
