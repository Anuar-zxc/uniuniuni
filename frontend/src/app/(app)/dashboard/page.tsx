"use client";

import Link from "next/link";
import { LineChart } from "@/components/line-chart";
import { Meter, ReadinessTrack } from "@/components/readiness";
import { buttonVariants } from "@/components/ui/button";
import { Panel, Section } from "@/components/ui/panel";
import { ErrorNote, Loading } from "@/components/ui/states";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { t, tx, locale } = useI18n();
  const { data, error, loading } = useApi<Dashboard>("/dashboard");
  if (loading) return <Loading />;
  if (error || !data) return <ErrorNote error={error} />;
  const r = data.readiness;
  const nba = data.next_best_action;
  const cats = Object.entries(r?.categories ?? {}).filter(([, c]) => c.weight > 0).sort((a, b) => b[1].weight - a[1].weight);

  return (
    <div>
      <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <section>
          <h1 className="text-2xl">{t("dash.readiness")}</h1>
          <div className="mt-6">
            {r ? <ReadinessTrack score={r.score} status={r.status} /> : <p className="text-muted">{t("dash.noData")}</p>}
          </div>
          {r?.confidence && (
            <p className="mt-4 text-sm text-muted">{t("dash.confidence")}: {tx(`dash.conf.${r.confidence}`)}</p>
          )}
        </section>

        <Panel className="flex flex-col justify-between gap-6 border-ink p-6">
          <div>
            <p className="text-sm text-muted">{t("dash.nba")}</p>
            <p className="mt-2 font-display text-xl font-semibold leading-snug">
              {tx(`nba.${nba.action}`)}{nba.mode && nba.action !== "retest" ? ` · ${tx(`mode.${nba.mode}`)}` : ""}
            </p>
            {nba.topic && <p className="mt-1 text-muted">{nba.topic}</p>}
          </div>
          <Link href={nba.href} className={buttonVariants({ className: "self-start" })}>{t("nba.go")}</Link>
        </Panel>
      </div>

      {r && r.risks.length > 0 && (
        <Section title={t("dash.risks")} className="mt-6 border-t border-line">
          <ol className="grid gap-6 md:grid-cols-3">
            {r.risks.map((risk, i) => (
              <li key={risk.title} className="flex gap-4">
                <span className="font-display text-3xl font-semibold leading-none text-muted">{i + 1}</span>
                <div>
                  <p className="font-medium">{tx(`cat.${risk.title}`, risk.title)}</p>
                  <p className="text-sm text-muted">{tx(`risk.${risk.type}`)} — {risk.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      <div className="grid gap-x-12 border-t border-line lg:grid-cols-2">
        <Section title={t("dash.progress")}>
          {data.progress.length ? <LineChart points={data.progress} locale={locale} /> : <p className="text-muted">{t("dash.noData")}</p>}
        </Section>
        <Section title={t("dash.categories")}>
          <div className="flex flex-col gap-4">
            {cats.length ? cats.map(([c, v]) => (
              <Meter key={c} label={`${tx(`cat.${c}`, c)} · ${Math.round(v.weight * 100)}%`} value={v.evidence ? v.score : null} />
            )) : <p className="text-muted">{t("dash.noData")}</p>}
          </div>
        </Section>
      </div>

      <div className="grid gap-x-12 border-t border-line md:grid-cols-3">
        <Section title={<span className="text-base">{t("dash.target")}</span>}>
          {data.target ? (
            <Link href={`/jobs/${data.target.job_id}`} className="block hover:underline">
              <p className="font-medium">{data.target.title}</p>
              <p className="text-sm text-muted">{data.target.company ?? ""}{data.target.match_score !== null ? ` · ${t("jobs.match")} ${Math.round(data.target.match_score)}%` : ""}</p>
            </Link>
          ) : <Link href="/jobs/new" className="text-muted underline underline-offset-2">{t("dash.noTarget")}</Link>}
          {data.upcoming_interview && (
            <p className="mt-4 text-sm">
              {t("dash.upcoming")}{" "}
              <span className="font-display text-lg font-semibold">
                {data.upcoming_interview.days_left > 0 ? `${data.upcoming_interview.days_left} ${t("dash.days")}` : t("dash.today")}
              </span>
            </p>
          )}
        </Section>
        <Section title={<span className="text-base">{t("dash.weakest")}</span>}>
          {data.weakest.length ? (
            <ul className="flex flex-col gap-2">
              {data.weakest.map((w) => (
                <li key={w.id}><Link href="/weaknesses" className="flex justify-between gap-3 hover:underline">
                  <span>{w.topic}</span><span className="tabular-nums text-muted">{Math.round(w.first_score)} → {Math.round(w.current_score)}</span>
                </Link></li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted">{t("dash.noData")}</p>}
        </Section>
        <Section title={<span className="text-base">{t("dash.training")}</span>}>
          {data.recommended_training.length ? (
            <ul className="flex flex-col gap-2">
              {data.recommended_training.map((tk) => (
                <li key={tk.id}><Link href={`/training#task-${tk.id}`} className="flex gap-3 hover:underline">
                  <span className="text-muted">{t("tr.day")} {tk.day}</span><span>{tk.topic}</span>
                </Link></li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted">{t("dash.noData")}</p>}
          {data.latest_interview && (
            <p className="mt-4 text-sm text-muted">
              {t("dash.latest")}:{" "}
              <Link href={`/interviews/${data.latest_interview.session_id}/report`} className="font-medium text-ink underline underline-offset-2">
                {Math.round(data.latest_interview.score ?? 0)}/100
              </Link>
            </p>
          )}
        </Section>
      </div>
    </div>
  );
}
