"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { en, type DictKey } from "./dict";
import { kk } from "./dict.kk";
import { ru } from "./dict.ru";

export type Locale = "ru" | "en" | "kk";
const DICTS: Record<Locale, Record<string, string>> = { en, ru, kk };
export const LOCALES: { code: Locale; label: string }[] = [
  { code: "ru", label: "Русский" },
  { code: "kk", label: "Қазақша" },
  { code: "en", label: "English" },
];

type Ctx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: DictKey) => string;
  /** Dynamic key lookup (e.g. `cat.${category}`); falls back to the provided default or the raw key. */
  tx: (key: string, fallback?: string) => string;
};

const I18nContext = createContext<Ctx | null>(null);

function readStored(): Locale | null {
  try {
    const v = window.localStorage.getItem("or_locale");
    return v === "ru" || v === "en" || v === "kk" ? v : null;
  } catch {
    return null;
  }
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ru");

  useEffect(() => {
    const stored = readStored();
    if (stored) setLocaleState(stored);
    else if (navigator.language.startsWith("en")) setLocaleState("en");
    else if (navigator.language.startsWith("kk")) setLocaleState("kk");
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      window.localStorage.setItem("or_locale", l);
    } catch {
      /* storage unavailable: keep in memory */
    }
  }, []);

  const value = useMemo<Ctx>(() => {
    const d = DICTS[locale];
    return {
      locale,
      setLocale,
      t: (key) => d[key] ?? en[key] ?? key,
      tx: (key, fallback) => d[key] ?? (en as Record<string, string>)[key] ?? fallback ?? key,
    };
  }, [locale, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}
