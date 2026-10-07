"use client";

import { ArrowDown, Clock, CornerDownRight } from "lucide-react";
import Link from "next/link";
import { Logo } from "@/components/app-shell";
import { LangSwitch } from "@/components/lang-switch";
import { ReadinessTrack } from "@/components/readiness";
import { buttonVariants } from "@/components/ui/button";
import type { DictKey } from "@/lib/dict";
import { useI18n } from "@/lib/i18n";
import { ThemeToggle } from "@/lib/theme";

const STEPS: [DictKey, DictKey][] = [
  ["landing.step1", "landing.step1.d"],
  ["landing.step2", "landing.step2.d"],
  ["landing.step3", "landing.step3.d"],
  ["landing.step4", "landing.step4.d"],
  ["landing.step5", "landing.step5.d"],
];
const FAQ: [DictKey, DictKey][] = [
  ["landing.faq.q1", "landing.faq.a1"],
  ["landing.faq.q2", "landing.faq.a2"],
  ["landing.faq.q3", "landing.faq.a3"],
  ["landing.faq.q4", "landing.faq.a4"],
];
const ATTEMPTS = [41, 63, 78];

export default function Landing() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-transparent bg-paper/85 backdrop-blur supports-[backdrop-filter]:bg-paper/70">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-8">
          <Logo />
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden sm:inline-flex"><LangSwitch /></span>
            <ThemeToggle />
            <Link href="/pricing" className="hidden px-2 text-sm text-muted hover:text-ink sm:inline">{t("nav.pricing")}</Link>
            <Link href="/login" className={buttonVariants({ variant: "outline", size: "sm" })}>{t("nav.login")}</Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero: the promise on the left, the product's most characteristic moment on the right */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 pt-10 sm:px-8 lg:grid-cols-[1fr_1.05fr] lg:gap-16 lg:pt-20">
          <div>
            <h1 className="max-w-[18ch] text-[clamp(2rem,1.3rem+2.6vw,3.25rem)] leading-[1.1]">{t("landing.title")}</h1>
            <p className="mt-6 max-w-[54ch] text-lg leading-relaxed text-muted">{t("landing.lead")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/register" className={buttonVariants({ size: "lg" })}>{t("landing.cta")}</Link>
              <a href="#how" className={buttonVariants({ variant: "ghost", size: "lg" })}>
                {t("landing.steps.title")} <ArrowDown size={16} aria-hidden />
              </a>
            </div>
            <p className="mt-6 text-sm text-muted">{t("landing.trust")}</p>
            <div className="mt-4 sm:hidden"><LangSwitch /></div>
          </div>
          <InterviewRoomDemo />
        </section>

        {/* CV → questions */}
        <Feature title={t("landing.cv.title")} lead={t("landing.cv.lead")}>
          <figure className="rounded-panel border border-line bg-raised p-6">
            <figcaption className="mb-3 text-sm text-muted">{t("nav.resume")} · {t("landing.example")}</figcaption>
            <blockquote className="border-l-2 border-ink pl-4 text-lg leading-snug">{t("landing.cv.bullet")}</blockquote>
            <ul className="mt-5 flex flex-col gap-2.5">
              {(["landing.cv.q1", "landing.cv.q2", "landing.cv.q3", "landing.cv.q4"] as DictKey[]).map((k) => (
                <li key={k} className="flex gap-2.5 text-[15px]">
                  <CornerDownRight size={16} className="mt-1 shrink-0 text-muted" aria-hidden />
                  {t(k)}
                </li>
              ))}
            </ul>
          </figure>
        </Feature>

        {/* Error memory with retest progress */}
        <Feature title={t("landing.memory.title")} lead={t("landing.memory.lead")} flip>
          <figure className="rounded-panel border border-line bg-raised p-6">
            <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-lg font-semibold">{t("landing.memory.topic")}</span>
              <span className="text-sm text-muted">{t("wk.status.improving")} · {t("landing.example")}</span>
            </figcaption>
            <div className="mt-6 flex h-40 items-end gap-4" role="img" aria-label={ATTEMPTS.join(" → ")}>
              {ATTEMPTS.map((v, i) => (
                <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-2">
                  <span className="font-display text-xl font-semibold tabular-nums">{v}</span>
                  <div className="w-full rounded-t-md bg-primary" style={{ height: `${v * 0.7}%`, opacity: 0.55 + i * 0.22 }} />
                  <span className="text-xs text-muted">{t("landing.memory.attempt")} {i + 1}</span>
                </div>
              ))}
            </div>
          </figure>
        </Feature>

        {/* Readiness */}
        <Feature title={t("landing.ready.title")} lead={t("landing.ready.lead")}>
          <figure className="rounded-panel border border-line bg-raised p-6">
            <figcaption className="mb-5 text-sm text-muted">{t("dash.readiness")} · {t("landing.example")}</figcaption>
            <ReadinessTrack score={72} status="ALMOST_READY" />
            <p className="mt-8 text-sm font-medium">{t("dash.risks")}</p>
            <ol className="mt-3 flex flex-col gap-2 text-[15px]">
              {(["landing.ready.r1", "landing.ready.r2", "landing.ready.r3"] as DictKey[]).map((k, i) => (
                <li key={k} className="flex gap-3">
                  <span className="font-display text-sm text-muted">{i + 1}</span>
                  {t(k)}
                </li>
              ))}
            </ol>
          </figure>
        </Feature>

        {/* The loop — a real sequence, so it's numbered */}
        <section id="how" className="scroll-mt-20 border-t border-line">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-8">
            <h2 className="max-w-xl text-3xl">{t("landing.steps.title")}</h2>
            <ol className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-5">
              {STEPS.map(([title, desc], i) => (
                <li key={title} className="border-t-2 border-ink pt-4">
                  <span className="font-display text-sm text-muted">{i + 1}</span>
                  <h3 className="mt-2">{t(title)}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-muted">{t(desc)}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-t border-line">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-8 lg:grid-cols-[1fr_2fr]">
            <h2 className="text-3xl">{t("landing.faq.title")}</h2>
            <div className="divide-y divide-line border-y border-line">
              {FAQ.map(([q, a]) => (
                <details key={q} className="group py-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-medium">
                    {t(q)}
                    <span className="text-muted transition-transform group-open:rotate-45" aria-hidden>+</span>
                  </summary>
                  <p className="mt-3 max-w-prose leading-relaxed text-muted">{t(a)}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-8">
          <div className="flex flex-col items-start gap-6 rounded-panel bg-ink px-6 py-12 text-paper sm:px-12 lg:flex-row lg:items-center lg:justify-between">
            <p className="max-w-2xl font-display text-xl leading-snug sm:text-2xl">{t("landing.promise")}</p>
            <Link href="/register" className={buttonVariants({ size: "lg", className: "bg-paper text-ink hover:bg-paper/90" })}>{t("landing.cta")}</Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-sm text-muted sm:px-8">
          <span>© OfferReady. {t("landing.footer")}</span>
          <span className="flex gap-5">
            <Link href="/pricing" className="hover:text-ink">{t("nav.pricing")}</Link>
            <Link href="/login" className="hover:text-ink">{t("nav.login")}</Link>
          </span>
        </div>
      </footer>
    </div>
  );
}

function Feature({ title, lead, flip, children }: { title: string; lead: string; flip?: boolean; children: React.ReactNode }) {
  return (
    <section className="border-t border-line">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 sm:px-8 lg:grid-cols-2 lg:gap-16">
        <div className={flip ? "lg:order-2" : ""}>
          <h2 className="max-w-[22ch] text-3xl leading-tight">{title}</h2>
          <p className="mt-4 max-w-[52ch] text-lg leading-relaxed text-muted">{lead}</p>
        </div>
        <div className={flip ? "lg:order-1" : ""}>{children}</div>
      </div>
    </section>
  );
}

/** A framed slice of the interview room: the follow-up that doesn't let a shallow answer pass. */
function InterviewRoomDemo() {
  const { t } = useI18n();
  return (
    <div className="overflow-hidden rounded-panel border border-line bg-raised shadow-[0_24px_60px_-30px_rgb(var(--ink)/0.35)]" aria-label={t("landing.room.title")}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3 text-sm">
        <span className="font-medium">{t("iv.question")} 3 {t("iv.of")} 8</span>
        <span className="flex items-center gap-4 text-muted">
          <span>{t("cat.project_deep_dive")}</span>
          <span className="flex items-center gap-1 tabular-nums"><Clock size={14} aria-hidden /> 12:41</span>
        </span>
      </div>
      <div className="flex h-1 gap-[2px] px-5 pt-3" aria-hidden>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i < 2 ? "bg-ink" : "bg-line"}`} />
        ))}
      </div>
      <div className="exchange flex flex-col gap-3 p-5 text-[15px] leading-relaxed">
        <div className="max-w-[92%] rounded-panel rounded-tl-sm border border-line bg-paper px-4 py-3">{t("landing.demo.q")}</div>
        <div className="ml-auto max-w-[85%] rounded-panel rounded-tr-sm bg-line/60 px-4 py-3">{t("landing.demo.a")}</div>
        <p className="flex items-center gap-2 pl-1 text-sm text-muted">
          <span className="h-2 w-2 rounded-full bg-status-needswork" aria-hidden />
          {t("landing.room.eval")}
        </p>
        <div className="max-w-[92%] rounded-panel rounded-tl-sm border border-ink bg-paper px-4 py-3 font-medium">{t("landing.demo.fu")}</div>
        <div className="ml-auto max-w-[85%] rounded-panel rounded-tr-sm bg-line/60 px-4 py-3 text-muted">{t("landing.demo.a2")}</div>
      </div>
    </div>
  );
}
