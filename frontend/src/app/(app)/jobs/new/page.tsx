"use client";

import { useRouter } from "next/navigation";
import { JobForm } from "@/components/job-views";
import { useMe } from "@/components/me-context";
import { useI18n } from "@/lib/i18n";

export default function NewJobPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { reload } = useMe();
  return (
    <div className="max-w-3xl">
      <h1>{t("jobs.add")}</h1>
      <div className="mt-8"><JobForm onDone={async (j) => { await reload(); router.push(`/jobs/${j.id}`); }} /></div>
    </div>
  );
}
