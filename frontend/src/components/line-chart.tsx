"use client";

import { useRef, useState } from "react";

type Point = { at: string; score: number };

/**
 * Single-series line (no legend: the section title names it). Band thresholds 45/65/80 are the only gridlines,
 * because they are where the readiness status changes. Crosshair + tooltip on hover/focus.
 */
export function LineChart({ points, height = 180, locale }: { points: Point[]; height?: number; locale: string }) {
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = 640;
  const H = height;
  const pad = { l: 30, r: 12, t: 12, b: 24 };
  const iw = W - pad.l - pad.r;
  const ih = H - pad.t - pad.b;
  const x = (i: number) => pad.l + (points.length <= 1 ? iw / 2 : (i / (points.length - 1)) * iw);
  const y = (v: number) => pad.t + ih - (v / 100) * ih;
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.score).toFixed(1)}`).join(" ");
  const fmt = (s: string) => new Date(s).toLocaleDateString(locale, { day: "numeric", month: "short" });

  const onMove = (e: React.PointerEvent) => {
    const r = ref.current?.getBoundingClientRect();
    if (!r || !points.length) return;
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = 0;
    points.forEach((_, i) => { if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i; });
    setHover(best);
  };

  const hp = hover !== null ? points[hover] : null;
  return (
    <div className="relative">
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} className="h-auto w-full touch-none" onPointerMove={onMove} onPointerLeave={() => setHover(null)}
        role="img" aria-label={points.map((p) => `${fmt(p.at)}: ${Math.round(p.score)}`).join(", ")}>
        {[45, 65, 80].map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} className="stroke-line" strokeDasharray="3 4" />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" className="fill-muted text-[11px]">{v}</text>
          </g>
        ))}
        <line x1={pad.l} x2={W - pad.r} y1={y(0)} y2={y(0)} className="stroke-line" />
        {points.length > 1 && <path d={d} fill="none" className="stroke-primary" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />}
        {points.map((p, i) => (
          <circle key={i} cx={x(i)} cy={y(p.score)} r={hover === i ? 5 : 4} className="fill-primary stroke-raised" strokeWidth={2} />
        ))}
        {hp && hover !== null && <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={pad.t + ih} className="stroke-muted" strokeWidth={1} />}
        {points.length > 0 && (
          <>
            <text x={x(0)} y={H - 6} textAnchor="start" className="fill-muted text-[11px]">{fmt(points[0].at)}</text>
            {points.length > 1 && <text x={x(points.length - 1)} y={H - 6} textAnchor="end" className="fill-muted text-[11px]">{fmt(points[points.length - 1].at)}</text>}
          </>
        )}
      </svg>
      {hp && hover !== null && (
        <div className="pointer-events-none absolute -translate-x-1/2 rounded-md border border-line bg-raised px-2 py-1 text-xs text-ink shadow-sm"
          style={{ left: `${(x(hover) / W) * 100}%`, top: 0 }}>
          <span className="font-medium tabular-nums">{Math.round(hp.score)}</span> <span className="text-muted">{fmt(hp.at)}</span>
        </div>
      )}
    </div>
  );
}
