"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { JobAnalysisView } from "@/components/job-views";
import { useMe } from "@/components/me-context";
import { Button, buttonVariants } from "@/components/ui/button";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Job } from "@/lib/types";

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useI18n();
  const { me, reload } = useMe();
  const { data: job, error, loading } = useApi<Job>(`/jobs/${id}`);
  if (loading) return <Loading />;
  if (error || !job) return <ErrorNote error={error} />;
  const active = me?.profile?.active_job_id === job.id;
  return (
    <div>
      <Link href="/jobs" className="text-sm text-muted hover:text-ink">{t("common.back")}</Link>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1>{job.title}</h1>
          <p className="mt-1 text-muted">{[job.company_name, job.level, job.interview_date].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!active && <Button variant="outline" onClick={async () => { await api.patch("/profile", { active_job_id: job.id }); await reload(); }}>{t("jobs.makeActive")}</Button>}
          <Link href={`/interviews/new?job=${job.id}&mode=mixed`} className={buttonVariants()}>{t("jobs.startInterview")}</Link>
        </div>
      </div>
      <div className="mt-4"><JobAnalysisView job={job} /></div>
    </div>
  );
}
