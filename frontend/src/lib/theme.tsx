"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "./i18n";

/** Applied before paint by the inline script in layout.tsx to avoid a flash. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem('or_theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`;

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { t } = useI18n();
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("or_theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
  };
  return (
    <button type="button" onClick={toggle} aria-label={t("common.theme")} title={t("common.theme")}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted hover:bg-line/50 hover:text-ink ${className}`}>
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
