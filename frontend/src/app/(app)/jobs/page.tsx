"use client";

import Link from "next/link";
import { useMe } from "@/components/me-context";
import { buttonVariants } from "@/components/ui/button";
import { Empty, Loading } from "@/components/ui/states";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Job } from "@/lib/types";

export default function JobsPage() {
  const { t } = useI18n();
  const { me } = useMe();
  const { data, loading } = useApi<Job[]>("/jobs");
  const add = <Link href="/jobs/new" className={buttonVariants()}>{t("jobs.add")}</Link>;
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4"><h1>{t("jobs.title")}</h1>{data?.length ? add : null}</div>
      <div className="mt-8">
        {loading ? <Loading /> : !data?.length ? <Empty action={add}>{t("jobs.empty")}</Empty> : (
          <ul className="divide-y divide-line border-y border-line">
            {data.map((j) => (
              <li key={j.id}>
                <Link href={`/jobs/${j.id}`} className="flex flex-wrap items-center justify-between gap-4 py-4 hover:bg-line/30 sm:px-2">
                  <div>
                    <p className="font-medium">{j.title}</p>
                    <p className="text-sm text-muted">
                      {[j.company_name, j.level, j.interview_date].filter(Boolean).join(" · ")}
                      {me?.profile?.active_job_id === j.id && <span className="ml-2 rounded-full bg-ink px-2 py-0.5 text-xs text-paper">{t("jobs.active")}</span>}
                    </p>
                  </div>
                  <span className="font-display text-2xl font-semibold tabular-nums">{j.match_score === null ? "—" : `${Math.round(j.match_score)}%`}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
