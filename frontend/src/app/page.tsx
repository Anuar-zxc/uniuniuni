"use client";

import Link from "next/link";
import { Logo } from "@/components/app-shell";
import { LangSwitch } from "@/components/lang-switch";
import { buttonVariants } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import type { DictKey } from "@/lib/dict";
import { ThemeToggle } from "@/lib/theme";

const STEPS: [DictKey, DictKey][] = [
  ["landing.step1", "landing.step1.d"],
  ["landing.step2", "landing.step2.d"],
  ["landing.step3", "landing.step3.d"],
  ["landing.step4", "landing.step4.d"],
  ["landing.step5", "landing.step5.d"],
];

export default function Landing() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-8">
        <Logo />
        <div className="flex items-center gap-2 sm:gap-3">
          <LangSwitch />
          <ThemeToggle />
          <Link href="/pricing" className="hidden text-sm text-muted hover:text-ink sm:inline">{t("nav.pricing")}</Link>
          <Link href="/login" className={buttonVariants({ variant: "ghost", size: "sm" })}>{t("nav.login")}</Link>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 pt-10 sm:px-8 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
          <div>
            <h1 className="max-w-[16ch] text-[clamp(2.1rem,1.4rem+3vw,3.6rem)] leading-[1.08]">{t("landing.title")}</h1>
            <p className="mt-6 max-w-prose text-lg text-muted">{t("landing.lead")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/register" className={buttonVariants({ size: "lg" })}>{t("landing.cta")}</Link>
              <Link href="/pricing" className={buttonVariants({ variant: "outline", size: "lg" })}>{t("landing.secondary")}</Link>
            </div>
          </div>

          {/* The characteristic moment of a real interview: the follow-up that doesn't let a shallow answer pass. */}
          <div className="exchange flex flex-col gap-3" aria-label="Interview example">
            <Bubble who="interviewer">{t("landing.demo.q")}</Bubble>
            <Bubble who="candidate">{t("landing.demo.a")}</Bubble>
            <p className="pl-1 text-sm text-muted">{t("landing.demo.note")}</p>
            <Bubble who="interviewer" strong>{t("landing.demo.fu")}</Bubble>
            <Bubble who="candidate">{t("landing.demo.a2")}</Bubble>
          </div>
        </section>

        <section className="border-t border-line">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-8">
            <h2 className="max-w-xl">{t("landing.steps.title")}</h2>
            <ol className="mt-10 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-5">
              {STEPS.map(([title, desc], i) => (
                <li key={title} className="relative border-t-2 border-ink pt-4">
                  <span className="font-display text-sm text-muted">{i + 1}</span>
                  <h3 className="mt-2">{t(title)}</h3>
                  <p className="mt-2 text-[15px] text-muted">{t(desc)}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-8">
          <div className="flex flex-col items-start gap-6 rounded-panel bg-ink px-6 py-10 text-paper sm:px-10 lg:flex-row lg:items-center lg:justify-between">
            <p className="max-w-2xl font-display text-xl leading-snug">{t("landing.promise")}</p>
            <Link href="/register" className={buttonVariants({ size: "lg", className: "bg-paper text-ink hover:bg-paper/90" })}>{t("landing.cta")}</Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-muted sm:px-8">© OfferReady. {t("landing.footer")}</div>
      </footer>
    </div>
  );
}

function Bubble({ who, strong, children }: { who: "interviewer" | "candidate"; strong?: boolean; children: React.ReactNode }) {
  if (who === "interviewer") {
    return (
      <div className={`max-w-[92%] rounded-panel rounded-tl-sm border px-4 py-3 ${strong ? "border-ink bg-raised font-medium" : "border-line bg-raised"}`}>
        {children}
      </div>
    );
  }
  return <div className="ml-auto max-w-[85%] rounded-panel rounded-tr-sm bg-line/60 px-4 py-3 text-ink">{children}</div>;
}
