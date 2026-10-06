"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Meter } from "@/components/readiness";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Chip, Section } from "@/components/ui/panel";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Resume } from "@/lib/types";

export function ResumeUploader({ onDone, compact }: { onDone: (r: Resume) => void; compact?: boolean }) {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [drag, setDrag] = useState(false);

  const run = async (fn: () => Promise<Resume>) => {
    setBusy(true);
    setError(null);
    try {
      onDone(await fn());
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const uploadFile = (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    void run(() => api.upload<Resume>("/resumes", fd));
  };

  if (busy) return <Loading label={t("resume.analyzing")} />;
  return (
    <div className="flex flex-col gap-4">
      <button type="button" onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) uploadFile(f); }}
        className={`flex flex-col items-center justify-center gap-2 rounded-panel border-2 border-dashed px-6 ${compact ? "py-8" : "py-12"} text-center ${drag ? "border-primary bg-primary/5" : "border-line hover:border-ink/40"}`}>
        <Upload size={22} className="text-muted" aria-hidden />
        <span className="font-medium text-ink">{t("resume.upload")}</span>
        <span className="text-sm text-muted">PDF · DOCX · TXT, ≤ 5 MB</span>
      </button>
      <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadFile(f); }} />
      <details className="group">
        <summary className="cursor-pointer text-sm text-muted hover:text-ink">{t("resume.orPaste")}</summary>
        <div className="mt-3 flex flex-col gap-3">
          <Textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} />
          <Button variant="outline" disabled={text.trim().length < 80} onClick={() => run(() => api.post<Resume>("/resumes/text", { text }))}>
            {t("resume.analyze")}
          </Button>
        </div>
      </details>
      <ErrorNote error={error} />
    </div>
  );
}

export function ResumeAnalysisView({ resume }: { resume: Resume }) {
  const { t } = useI18n();
  const a = resume.analysis;
  const s = a.scores;
  return (
    <div className="divide-y divide-line">
      <Section>
        <div className="grid gap-10 md:grid-cols-[220px_1fr]">
          <div>
            <p className="text-sm text-muted">{t("resume.score")}</p>
            <p className="mt-1 font-display text-6xl font-semibold leading-none">{Math.round(resume.overall_score ?? a.overall ?? 0)}</p>
            <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-muted">{t("resume.seniority")}</dt><dd className="font-medium capitalize">{a.seniority}</dd></div>
              <div><dt className="text-muted">{t("resume.years")}</dt><dd className="font-medium">{a.years_experience || "—"}</dd></div>
            </dl>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Meter label={t("resume.ats")} value={s.ats} />
            <Meter label={t("resume.technical")} value={s.technical} />
            <Meter label={t("resume.impact")} value={s.impact} />
            <Meter label={t("resume.clarity")} value={s.clarity} />
            <Meter label={t("resume.experience")} value={s.experience} />
          </div>
        </div>
      </Section>

      {a.technologies.length > 0 && (
        <Section title={t("resume.technologies")}>
          <div className="flex flex-wrap gap-2">{a.technologies.map((x) => <Chip key={x}>{x}</Chip>)}</div>
        </Section>
      )}

      {a.likely_questions.length > 0 && (
        <Section title={t("resume.questions")}>
          <div className="flex flex-col gap-6">
            {a.likely_questions.map((lq, i) => (
              <figure key={i} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] md:gap-8">
                <blockquote className="border-l-2 border-ink pl-4 text-ink">{lq.bullet}</blockquote>
                <ul className="flex flex-col gap-1.5 text-[15px] text-muted">
                  {lq.questions.map((q, j) => <li key={j}>— {q}</li>)}
                </ul>
              </figure>
            ))}
          </div>
        </Section>
      )}

      <div className="grid gap-x-10 md:grid-cols-3">
        <ListBlock title={t("resume.achievements")} items={a.measurable_impact} />
        <ListBlock title={t("resume.missing")} items={a.missing_information} />
        <ListBlock title={t("resume.suspicious")} items={a.suspicious_claims} />
      </div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  const { t } = useI18n();
  return (
    <Section title={<span className="text-base">{title}</span>}>
      {items.length ? (
        <ul className="flex list-disc flex-col gap-1.5 pl-5 text-[15px]">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
      ) : <p className="text-sm text-muted">{t("common.none")}</p>}
    </Section>
  );
}
