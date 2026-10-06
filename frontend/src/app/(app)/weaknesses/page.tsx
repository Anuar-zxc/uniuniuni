"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/panel";
import { Empty, Loading } from "@/components/ui/states";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Weakness } from "@/lib/types";
import { cn } from "@/lib/utils";

const SEV_DOT: Record<string, string> = {
  critical: "bg-status-notready", high: "bg-status-needswork", medium: "bg-status-almost", low: "bg-status-ready",
};

export default function WeaknessesPage() {
  const { t, tx, locale } = useI18n();
  const { data, loading } = useApi<Weakness[]>("/weaknesses");
  const [filter, setFilter] = useState<"active" | "resolved" | "all">("active");
  const list = (data ?? []).filter((w) => filter === "all" || (filter === "resolved" ? w.status === "resolved" : w.status !== "resolved"));
  return (
    <div>
      <h1>{t("wk.title")}</h1>
      <p className="mt-3 max-w-prose text-muted">{t("wk.lead")}</p>
      <div className="mt-6 inline-flex rounded-lg border border-line p-0.5" role="group">
        {(["active", "resolved", "all"] as const).map((f) => (
          <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
            className={cn("rounded-md px-3 py-1.5 text-sm", filter === f ? "bg-ink text-paper" : "text-muted hover:text-ink")}>
            {tx(`wk.filter.${f}`)}
          </button>
        ))}
      </div>
      <div className="mt-6 flex flex-col gap-4">
        {loading ? <Loading /> : !list.length ? <Empty>{t("wk.empty")}</Empty> : list.map((w) => (
          <Panel key={w.id} className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-lg">{w.topic}</h3>
                <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
                  <span>{tx(`cat.${w.category}`, w.category)}</span>
                  <span className="inline-flex items-center gap-1.5 text-ink"><span className={cn("h-2 w-2 rounded-full", SEV_DOT[w.severity])} />{tx(`sev.${w.severity}`)}</span>
                  <span>{tx(`wk.status.${w.status}`)}</span>
                </p>
              </div>
              <dl className="flex gap-6 text-sm">
                <div><dt className="text-muted">{t("wk.attempts")}</dt><dd className="font-display text-xl tabular-nums">{w.attempts}</dd></div>
                <div><dt className="text-muted">{t("wk.first")}</dt><dd className="font-display text-xl tabular-nums">{Math.round(w.first_score)}</dd></div>
                <div><dt className="text-muted">{t("wk.current")}</dt><dd className="font-display text-xl tabular-nums">{Math.round(w.current_score)}</dd></div>
              </dl>
            </div>
            {w.history.length > 1 && (
              <div className="mt-4 flex items-end gap-1" role="img" aria-label={w.history.map((h) => Math.round(h.score)).join(" → ")}>
                {w.history.map((h, i) => (
                  <div key={i} title={`${Math.round(h.score)} · ${h.source}`} className="w-3 rounded-t-sm bg-primary" style={{ height: `${Math.max(4, h.score * 0.4)}px` }} />
                ))}
              </div>
            )}
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-medium">{t("wk.exercise")}: <span className="font-normal">{w.recommended_exercise}</span></summary>
              <div className="mt-4 grid gap-5 md:grid-cols-2">
                <Field title={t("wk.question")} text={w.question_text} />
                <Field title={t("wk.original")} text={w.original_answer} quote />
                <Field title={t("wk.why")} text={w.why_weak} />
                <Field title={t("wk.correct")} text={w.correct_concept} />
              </div>
              {w.next_retest_at && <p className="mt-4 text-sm text-muted">{t("wk.nextRetest")}: {new Date(w.next_retest_at).toLocaleDateString(locale)}</p>}
            </details>
          </Panel>
        ))}
      </div>
    </div>
  );
}

function Field({ title, text, quote }: { title: string; text: string; quote?: boolean }) {
  if (!text) return null;
  return (
    <div>
      <p className="mb-1 text-sm font-medium">{title}</p>
      <p className={cn("whitespace-pre-wrap text-[15px]", quote ? "text-muted" : "")}>{quote ? `“${text}”` : text}</p>
    </div>
  );
}
