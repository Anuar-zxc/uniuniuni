"use client";

import { useI18n } from "@/lib/i18n";
import type { ReadinessStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export const ZONES: { status: ReadinessStatus; from: number; to: number; cls: string; fill: string }[] = [
  { status: "NOT_READY", from: 0, to: 45, cls: "bg-status-notready", fill: "bg-status-notready/15" },
  { status: "NEEDS_WORK", from: 45, to: 65, cls: "bg-status-needswork", fill: "bg-status-needswork/15" },
  { status: "ALMOST_READY", from: 65, to: 80, cls: "bg-status-almost", fill: "bg-status-almost/15" },
  { status: "READY", from: 80, to: 100, cls: "bg-status-ready", fill: "bg-status-ready/15" },
];

export function StatusBadge({ status, className }: { status: ReadinessStatus; className?: string }) {
  const { tx } = useI18n();
  const zone = ZONES.find((z) => z.status === status) ?? ZONES[0];
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm font-medium text-ink", className)}>
      <span className={cn("h-2.5 w-2.5 rounded-full", zone.cls)} aria-hidden />
      {tx(`st.${status}`)}
    </span>
  );
}

/** Signature element: the pressure → confidence track. The candidate's marker travels across four zones. */
export function ReadinessTrack({ score, status, size = "lg" }: { score: number; status: ReadinessStatus; size?: "lg" | "sm" }) {
  const { tx, t } = useI18n();
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div className="flex items-baseline gap-2">
          <span className={cn("font-display font-semibold leading-none tracking-tight text-ink", size === "lg" ? "text-6xl sm:text-7xl" : "text-4xl")}>
            {Math.round(pct)}
          </span>
          <span className="text-muted">{t("common.of100")}</span>
        </div>
        <StatusBadge status={status} className="mb-1" />
      </div>
      <div className="relative mt-5" role="img" aria-label={`${Math.round(pct)} / 100 — ${tx(`st.${status}`)}`}>
        <div className="flex h-3 gap-[2px] overflow-hidden rounded-full">
          {ZONES.map((z) => (
            <div key={z.status} style={{ width: `${z.to - z.from}%` }} className={cn("h-full", z.status === status ? z.cls : z.fill)} />
          ))}
        </div>
        <div className="absolute -top-1.5 h-6 w-[3px] -translate-x-1/2 rounded-full bg-ink ring-2 ring-paper transition-[left] duration-700" style={{ left: `${pct}%` }} />
      </div>
      {size === "lg" && (
        <div className="mt-2 hidden text-xs text-muted sm:flex">
          {ZONES.map((z) => (
            <span key={z.status} style={{ width: `${z.to - z.from}%` }} className={cn("truncate pr-1", z.status === status && "font-medium text-ink")}>
              {tx(`st.${z.status}`)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Neutral meter for sub-scores (status colors are reserved for readiness). */
export function Meter({ label, value, hint }: { label: string; value: number | null | undefined; hint?: string }) {
  const v = value ?? 0;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
        <span className="text-ink">{label}</span>
        <span className="tabular-nums font-medium text-ink">{value === null || value === undefined ? "—" : Math.round(v)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-line">
        <div className="h-1.5 rounded-full bg-primary" style={{ width: `${Math.max(2, Math.min(100, v))}%` }} />
      </div>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function statusFor(score: number): ReadinessStatus {
  return score >= 80 ? "READY" : score >= 65 ? "ALMOST_READY" : score >= 45 ? "NEEDS_WORK" : "NOT_READY";
}
