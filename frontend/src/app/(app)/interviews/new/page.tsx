"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useMe } from "@/components/me-context";
import { Button } from "@/components/ui/button";
import { Label, Select } from "@/components/ui/input";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { LOCALES, useI18n } from "@/lib/i18n";
import type { Job, SessionState } from "@/lib/types";
import { cn } from "@/lib/utils";

const MODES = ["mixed", "technical", "coding", "system_design", "behavioral", "project_deep_dive", "hr", "recruiter_screening",
  "frontend", "backend", "ml", "devops"];

function NewInterview() {
  const { t, tx, locale } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const { me } = useMe();
  const { data: jobs } = useApi<Job[]>("/jobs");
  const [mode, setMode] = useState(params.get("mode") ?? "mixed");
  const [jobId, setJobId] = useState<string>(params.get("job") ?? "");
  const [language, setLanguage] = useState<string>(locale);
  const [difficulty, setDifficulty] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!jobId && me?.profile?.active_job_id) setJobId(String(me.profile.active_job_id));
    if (me?.profile?.language) setLanguage(me.profile.language);
  }, [me]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const s = await api.post<SessionState>("/interviews", {
        mode, language, job_id: jobId ? Number(jobId) : null, difficulty: difficulty ? Number(difficulty) : null,
      });
      router.push(`/interviews/${s.session_id}`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  if (busy) return <Loading label={t("iv.starting")} />;
  return (
    <div className="max-w-3xl">
      <h1>{t("iv.new")}</h1>
      <fieldset className="mt-8">
        <legend className="mb-3 text-sm font-medium">{t("iv.mode")}</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {MODES.map((m) => (
            <button key={m} type="button" onClick={() => setMode(m)} aria-pressed={mode === m}
              className={cn("rounded-lg border px-3 py-2.5 text-left text-[15px]", mode === m ? "border-ink bg-ink text-paper" : "border-line bg-raised hover:border-ink/40")}>
              {tx(`mode.${m}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div><Label htmlFor="job">{t("iv.target")}</Label>
          <Select id="job" value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">{t("iv.noTarget")}</option>
            {jobs?.map((j) => <option key={j.id} value={j.id}>{j.title}{j.company_name ? ` — ${j.company_name}` : ""}</option>)}
          </Select></div>
        <div><Label htmlFor="lang">{t("iv.language")}</Label>
          <Select id="lang" value={language} onChange={(e) => setLanguage(e.target.value)}>
            {LOCALES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </Select></div>
        <div><Label htmlFor="diff">{t("iv.difficulty")}</Label>
          <Select id="diff" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="">{t("iv.difficulty.auto")}</option>
            {[1, 2, 3, 4, 5].map((d) => <option key={d} value={d}>{d}</option>)}
          </Select></div>
      </div>
      <div className="mt-6"><ErrorNote error={error} /></div>
      <Button size="lg" className="mt-4" onClick={start}>{t("iv.start")}</Button>
    </div>
  );
}

export default function Page() {
  return <Suspense><NewInterview /></Suspense>;
}
