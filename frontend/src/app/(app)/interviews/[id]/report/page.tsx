"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Meter, ReadinessTrack } from "@/components/readiness";
import { Button, buttonVariants } from "@/components/ui/button";
import { Section } from "@/components/ui/panel";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Report, SessionState } from "@/lib/types";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, tx, locale } = useI18n();
  const { data: r, error, loading } = useApi<Report>(`/interviews/sessions/${id}/report`);
  const [retestError, setRetestError] = useState<unknown>(null);
  if (loading) return <Loading />;
  if (error || !r) return <ErrorNote error={error} />;

  const retest = async () => {
    try {
      const s = await api.post<SessionState>(`/interviews/${r.interview_id}/retest`);
      router.push(`/interviews/${s.session_id}`);
    } catch (e) {
      setRetestError(e);
    }
  };
  const delta = r.previous_overall !== null ? Math.round(r.overall - r.previous_overall) : null;

  return (
    <div>
      <Link href="/interviews" className="text-sm text-muted hover:text-ink">{t("common.back")}</Link>
      <h1 className="mt-3">{t("rep.title")}</h1>
      <p className="mt-1 text-muted">{tx(`mode.${r.mode}`, r.mode)} · {r.title.split("—")[1]?.trim()}</p>

      <div className="mt-8 grid gap-10 lg:grid-cols-[260px_1fr]">
        <div>
          <p className="text-sm text-muted">{t("rep.overall")}</p>
          <p className="mt-1 font-display text-7xl font-semibold leading-none">{Math.round(r.overall)}</p>
          {delta !== null && (
            <p className="mt-2 text-sm text-muted">{t("rep.prev")}: {Math.round(r.previous_overall!)} ({delta >= 0 ? "+" : ""}{delta})</p>
          )}
        </div>
        <div>
          <p className="mb-3 text-sm text-muted">{t("rep.readiness")}</p>
          <ReadinessTrack score={r.readiness.score} status={r.readiness.status} size="sm" />
        </div>
      </div>

      {r.summary && <p className="mt-8 max-w-prose text-lg leading-relaxed">{r.summary}</p>}
      {r.top_recommendations.length > 0 && (
        <ul className="mt-4 flex max-w-prose list-disc flex-col gap-1.5 pl-5">{r.top_recommendations.map((x, i) => <li key={i}>{x}</li>)}</ul>
      )}
      <div className="mt-6 flex flex-wrap gap-3">
        <Link href="/training" className={buttonVariants()}>{t("rep.training")}</Link>
        <Button variant="outline" onClick={retest}>{t("iv.retest")}</Button>
      </div>
      <div className="mt-3"><ErrorNote error={retestError} /></div>

      <Section title={t("rep.dimensions")} className="mt-8 border-t border-line">
        <div className="grid gap-x-10 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          {r.dimensions.map((d) => <Meter key={d.key} label={tx(`dim.${d.key}`, d.key)} value={d.score} />)}
        </div>
      </Section>

      <div className="divide-y divide-line border-t border-line">
        {r.dimensions.filter((d) => d.strengths.length || d.weaknesses.length || d.examples.worst).map((d) => (
          <details key={d.key} className="group py-4">
            <summary className="flex cursor-pointer items-baseline justify-between gap-4">
              <h3>{tx(`dim.${d.key}`, d.key)}</h3><span className="font-display tabular-nums">{Math.round(d.score)}</span>
            </summary>
            <div className="mt-4 grid gap-6 md:grid-cols-3">
              <Block title={t("rep.strengths")} items={d.strengths} />
              <Block title={t("rep.weaknesses")} items={d.weaknesses} />
              <Block title={t("rep.recommendations")} items={d.recommendations} />
            </div>
            {d.examples.worst && (
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {d.examples.best && d.examples.best.question !== d.examples.worst.question && (
                  <Example title={t("rep.example.best")} ex={d.examples.best} />
                )}
                <Example title={t("rep.example.worst")} ex={d.examples.worst} missed={t("rep.missed")} />
              </div>
            )}
          </details>
        ))}
      </div>

      <Section title={t("rep.topics")} className="border-t border-line">
        <ul className="divide-y divide-line">
          {r.topics.map((tp, i) => (
            <li key={i} className="flex flex-wrap items-baseline justify-between gap-3 py-2.5">
              <span>{tp.topic} <span className="text-sm text-muted">· {tx(`cat.${tp.category}`, tp.category)}{tp.followups ? ` · ${tp.followups} ${t("rep.followups")}` : ""}{tp.retest ? ` · ${t("rep.retest")}` : ""}</span></span>
              <span className="font-display tabular-nums">{Math.round(tp.score)}</span>
            </li>
          ))}
        </ul>
      </Section>

      {r.attempts.length > 1 && (
        <Section title={t("rep.attempts")} className="border-t border-line">
          <ol className="flex flex-wrap gap-6">
            {r.attempts.map((a, i) => (
              <li key={a.session_id}>
                <Link href={`/interviews/${a.session_id}/report`} className={a.session_id === r.session_id ? "font-medium" : "text-muted hover:text-ink"}>
                  #{i + 1} · <span className="font-display tabular-nums">{Math.round(a.score ?? 0)}</span>
                  <span className="ml-1 text-xs">{a.finished_at ? new Date(a.finished_at).toLocaleDateString(locale) : ""}</span>
                </Link>
              </li>
            ))}
          </ol>
        </Section>
      )}

      <details className="border-t border-line py-6">
        <summary className="cursor-pointer"><h2 className="inline">{t("rep.transcript")}</h2></summary>
        <div className="mt-4 flex max-w-3xl flex-col gap-3">
          {r.transcript.map((m, i) => (
            <p key={i} className={m.role === "interviewer" ? "font-medium" : "pl-4 text-muted"}>{m.text}</p>
          ))}
        </div>
      </details>
    </div>
  );
}

function Block({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{title}</p>
      <ul className="flex list-disc flex-col gap-1 pl-5 text-[15px]">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}

function Example({ title, ex, missed }: { title: string; ex: { question: string; answer: string; score: number; missing_points?: string[] }; missed?: string }) {
  return (
    <figure className="rounded-panel border border-line bg-raised p-4">
      <figcaption className="mb-2 flex justify-between text-sm text-muted"><span>{title}</span><span className="tabular-nums">{Math.round(ex.score)}</span></figcaption>
      <p className="text-sm font-medium">{ex.question}</p>
      <p className="mt-2 text-[15px] text-muted">“{ex.answer}”</p>
      {missed && ex.missing_points && ex.missing_points.length > 0 && (
        <p className="mt-3 text-sm"><span className="font-medium">{missed}:</span> {ex.missing_points.join("; ")}</p>
      )}
    </figure>
  );
}
