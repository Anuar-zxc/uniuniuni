"use client";

import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Empty, Loading } from "@/components/ui/states";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { SessionSummary } from "@/lib/types";

export default function InterviewsPage() {
  const { t, tx, locale } = useI18n();
  const { data, loading } = useApi<SessionSummary[]>("/interviews/sessions");
  const start = <Link href="/interviews/new" className={buttonVariants()}>{t("iv.new")}</Link>;
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4"><h1>{t("iv.title")}</h1>{data?.length ? start : null}</div>
      <div className="mt-8">
        {loading ? <Loading /> : !data?.length ? <Empty action={start}>{t("iv.empty")}</Empty> : (
          <ul className="divide-y divide-line border-y border-line">
            {data.map((s) => {
              const href = s.status === "completed" ? `/interviews/${s.session_id}/report` : `/interviews/${s.session_id}`;
              return (
                <li key={s.session_id}>
                  <Link href={href} className="flex flex-wrap items-center justify-between gap-4 py-4 hover:bg-line/30 sm:px-2">
                    <div>
                      <p className="font-medium">{tx(`mode.${s.mode}`, s.mode)}</p>
                      <p className="text-sm text-muted">
                        {s.title.split("—")[1]?.trim()} · {s.started_at ? new Date(s.started_at).toLocaleDateString(locale) : ""} · {tx(`iv.status.${s.status}`)}
                      </p>
                    </div>
                    <span className="font-display text-2xl font-semibold tabular-nums">{s.overall_score === null ? "—" : Math.round(s.overall_score)}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
