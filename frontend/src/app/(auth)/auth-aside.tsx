"use client";

import { ReadinessTrack } from "@/components/readiness";
import { useI18n } from "@/lib/i18n";

/** Right-hand panel on auth pages: one real moment from the product instead of marketing copy. */
export function AuthAside() {
  const { t } = useI18n();
  return (
    <aside className="relative hidden overflow-hidden border-l border-line bg-raised lg:flex lg:flex-col lg:justify-center lg:px-14">
      <div className="max-w-md">
        <p className="font-display text-2xl font-semibold leading-snug text-ink">{t("auth.side.title")}</p>
        <div className="mt-10 flex flex-col gap-3 text-[15px]">
          <div className="max-w-[92%] rounded-panel rounded-tl-sm border border-line bg-paper px-4 py-3">{t("landing.demo.q")}</div>
          <div className="ml-auto max-w-[85%] rounded-panel rounded-tr-sm bg-line/60 px-4 py-3">{t("landing.demo.a")}</div>
          <div className="max-w-[92%] rounded-panel rounded-tl-sm border border-ink bg-paper px-4 py-3 font-medium">{t("landing.demo.fu")}</div>
        </div>
        <div className="mt-10 rounded-panel border border-line bg-paper p-5">
          <p className="mb-3 text-sm text-muted">{t("dash.readiness")} · {t("landing.example")}</p>
          <ReadinessTrack score={72} status="ALMOST_READY" size="sm" />
        </div>
      </div>
    </aside>
  );
}
