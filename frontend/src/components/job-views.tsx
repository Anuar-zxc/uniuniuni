"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Chip, Section } from "@/components/ui/panel";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Job } from "@/lib/types";
import { cn } from "@/lib/utils";

export function JobForm({ onDone }: { onDone: (j: Job) => void }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ title: "", company_name: "", description: "", interview_date: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onDone(await api.post<Job>("/jobs", {
        title: form.title || null, company_name: form.company_name || null, description: form.description,
        interview_date: form.interview_date || null,
      }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  if (busy) return <Loading />;
  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div><Label htmlFor="title">{t("jobs.form.title")}</Label><Input id="title" value={form.title} onChange={set("title")} /></div>
        <div><Label htmlFor="company">{t("jobs.form.company")}</Label><Input id="company" value={form.company_name} onChange={set("company_name")} /></div>
      </div>
      <div><Label htmlFor="desc" hint={t("jobs.form.descriptionHint")}>{t("jobs.form.description")}</Label>
        <Textarea id="desc" required minLength={40} rows={10} value={form.description} onChange={set("description")} /></div>
      <div className="max-w-xs"><Label htmlFor="date">{t("jobs.form.date")}</Label><Input id="date" type="date" value={form.interview_date} onChange={set("interview_date")} /></div>
      <ErrorNote error={error} />
      <div><Button type="submit" disabled={form.description.trim().length < 40}>{t("jobs.form.submit")}</Button></div>
    </form>
  );
}

export function JobAnalysisView({ job }: { job: Job }) {
  const { t, tx } = useI18n();
  const m = job.match;
  const weights = Object.entries(job.blueprint.weights ?? {}).sort((a, b) => b[1] - a[1]);
  const topics = job.blueprint.topics ?? [];
  return (
    <div className="divide-y divide-line">
      <Section>
        <div className="grid gap-8 md:grid-cols-[200px_1fr]">
          <div>
            <p className="text-sm text-muted">{t("jobs.match")}</p>
            <p className="mt-1 font-display text-6xl font-semibold leading-none">{job.match_score === null ? "—" : `${Math.round(job.match_score)}%`}</p>
            <p className="mt-4 text-sm text-muted">{t("jobs.difficulty")}: <span className="font-medium text-ink">{job.analysis.expected_difficulty ?? "—"}/5</span></p>
          </div>
          <div className="grid gap-6 sm:grid-cols-3">
            <SkillList title={t("jobs.strong")} items={m.strong} tone="strong" />
            <SkillList title={t("jobs.weak")} items={m.weak} tone="weak" />
            <SkillList title={t("jobs.missing")} items={m.missing} tone="missing" />
          </div>
        </div>
      </Section>

      {weights.length > 0 && (
        <Section title={t("jobs.blueprint")}>
          <p className="-mt-2 mb-4 text-sm text-muted">{t("jobs.blueprint.d")}</p>
          {/* Part-to-whole of one interview: a single stacked bar, segments labelled directly below. */}
          <div className="flex h-3 gap-[2px] overflow-hidden rounded-full" role="img"
            aria-label={weights.map(([c, w]) => `${tx(`cat.${c}`, c)} ${Math.round(w * 100)}%`).join(", ")}>
            {weights.map(([c, w], i) => (
              <div key={c} style={{ width: `${w * 100}%`, opacity: 1 - i * 0.11 }} className="h-full bg-primary" />
            ))}
          </div>
          <ul className="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            {weights.map(([c, w]) => (
              <li key={c} className="flex justify-between gap-3 border-b border-line pb-1">
                <span>{tx(`cat.${c}`, c)}</span><span className="tabular-nums text-muted">{Math.round(w * 100)}%</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="grid gap-x-10 md:grid-cols-2">
        <Section title={<span className="text-base">{t("jobs.stages")}</span>}>
          <ol className="flex flex-col gap-2">
            {(m.likely_stages ?? job.analysis.likely_stages ?? []).map((s, i) => (
              <li key={i} className="flex gap-3"><span className="font-display text-sm text-muted">{i + 1}</span>{s}</li>
            ))}
          </ol>
        </Section>
        <Section title={<span className="text-base">{t("jobs.topics")}</span>}>
          <ul className="flex flex-col gap-1.5 text-[15px]">
            {topics.slice(0, 10).map((tp) => (
              <li key={tp.topic} className="flex items-center justify-between gap-3">
                <span>{tp.topic}</span>
                <span className="tabular-nums text-sm text-muted">{Math.round(tp.probability * 100)}%</span>
              </li>
            ))}
          </ul>
        </Section>
      </div>
    </div>
  );
}

function SkillList({ title, items, tone }: { title: string; items?: string[]; tone: "strong" | "weak" | "missing" }) {
  const { t } = useI18n();
  return (
    <div>
      <h3 className="mb-3 text-base">{title}</h3>
      {items && items.length ? (
        <div className="flex flex-wrap gap-2">
          {items.map((s) => (
            <Chip key={s} className={cn(tone === "strong" && "border-ink", tone === "missing" && "border-dashed text-muted")}>{s}</Chip>
          ))}
        </div>
      ) : <p className="text-sm text-muted">{t("common.none")}</p>}
    </div>
  );
}
