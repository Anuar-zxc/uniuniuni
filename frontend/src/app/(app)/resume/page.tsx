"use client";

import { useState } from "react";
import { ResumeAnalysisView, ResumeUploader } from "@/components/resume-views";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/states";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Resume } from "@/lib/types";

export default function ResumePage() {
  const { t } = useI18n();
  const { data, setData, loading } = useApi<Resume[]>("/resumes");
  const [replace, setReplace] = useState(false);
  if (loading) return <Loading />;
  const current = data?.find((r) => r.is_primary) ?? data?.[0];
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1>{t("resume.title")}</h1>
        {current && !replace && <Button variant="outline" onClick={() => setReplace(true)}>{t("resume.replace")}</Button>}
      </div>
      {current?.filename && !replace && <p className="mt-2 text-sm text-muted">{current.filename}</p>}
      <div className="mt-6">
        {!current || replace ? (
          <div className="max-w-2xl">
            {!current && <p className="mb-6 text-muted">{t("resume.empty")}</p>}
            <ResumeUploader onDone={(r) => { setData([r, ...(data ?? [])]); setReplace(false); }} />
          </div>
        ) : <ResumeAnalysisView resume={current} />}
      </div>
    </div>
  );
}
