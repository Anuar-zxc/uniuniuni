"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { isQuotaError } from "@/lib/api";

export function Loading({ label }: { label?: string }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-2 py-10 text-muted" role="status">
      <Loader2 className="animate-spin" size={18} /> {label ?? t("common.loading")}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const { t } = useI18n();
  if (!error) return null;
  if (isQuotaError(error)) {
    return (
      <p className="rounded-lg border border-status-needswork/40 bg-status-needswork/10 px-3 py-2 text-sm text-ink">
        {t("price.quota")}{" "}
        <Link href="/pricing" className="font-medium underline underline-offset-2">{t("price.upgrade")}</Link>
      </p>
    );
  }
  const msg = error instanceof Error && error.message ? error.message : t("common.error");
  return <p role="alert" className="rounded-lg border border-status-notready/40 bg-status-notready/10 px-3 py-2 text-sm text-ink">{msg}</p>;
}

export function Empty({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="rounded-panel border border-dashed border-line px-6 py-10 text-center">
      <p className="mx-auto max-w-md text-muted">{children}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
