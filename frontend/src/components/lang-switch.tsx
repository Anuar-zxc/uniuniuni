"use client";

import { LOCALES, useI18n, type Locale } from "@/lib/i18n";
import { api } from "@/lib/api";

export function LangSwitch({ persist = false }: { persist?: boolean }) {
  const { locale, setLocale } = useI18n();
  return (
    <div className="inline-flex rounded-lg border border-line p-0.5" role="group" aria-label="Language">
      {LOCALES.map((l) => (
        <button key={l.code} type="button" aria-pressed={locale === l.code} title={l.label}
          onClick={() => {
            setLocale(l.code as Locale);
            if (persist) void api.patch("/profile", { locale: l.code }).catch(() => {});
          }}
          className={`rounded-md px-2 py-1 text-xs font-medium ${locale === l.code ? "bg-ink text-paper" : "text-muted hover:text-ink"}`}>
          {l.code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
