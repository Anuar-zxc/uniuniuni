"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/app-shell";
import { LangSwitch } from "@/components/lang-switch";
import { Button } from "@/components/ui/button";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { ThemeToggle } from "@/lib/theme";
import type { Me, Plan } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function PricingPage() {
  const { t, tx, locale } = useI18n();
  const router = useRouter();
  const { data: plans, loading } = useApi<Plan[]>("/billing/plans");
  const [me, setMe] = useState<Me | null>(null);
  const [currency, setCurrency] = useState<"KZT" | "USD">(locale === "en" ? "USD" : "KZT");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => { api.peek<Me>("/profile").then(setMe).catch(() => setMe(null)); }, []);

  const choose = async (code: string) => {
    if (!me) return router.push("/register");
    try {
      const r = await api.post<{ redirect_url: string }>("/billing/checkout", { plan_code: code, currency });
      window.location.href = r.redirect_url;
    } catch (e) {
      setError(e);
    }
  };
  const price = (p: Plan) => {
    const v = p.prices[currency] ?? 0;
    if (!v) return t("price.free");
    return new Intl.NumberFormat(locale === "kk" ? "kk-KZ" : locale, { style: "currency", currency, maximumFractionDigits: 0 }).format(v);
  };

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-8">
        <Logo />
        <div className="flex items-center gap-2"><LangSwitch /><ThemeToggle />
          <Link href={me ? "/dashboard" : "/login"} className="text-sm text-muted hover:text-ink">{me ? t("nav.dashboard") : t("nav.login")}</Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><h1>{t("price.title")}</h1><p className="mt-3 text-muted">{t("price.lead")}</p></div>
          <div className="inline-flex rounded-lg border border-line p-0.5" role="group" aria-label="Currency">
            {(["KZT", "USD"] as const).map((c) => (
              <button key={c} onClick={() => setCurrency(c)} aria-pressed={currency === c}
                className={cn("rounded-md px-3 py-1 text-sm", currency === c ? "bg-ink text-paper" : "text-muted")}>{c}</button>
            ))}
          </div>
        </div>
        <div className="mt-6"><ErrorNote error={error} /></div>
        {loading ? <Loading /> : (
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {plans?.map((p) => {
              const current = me?.plan.code === p.code;
              const featured = p.code === "pro";
              return (
                <div key={p.code} className={cn("flex flex-col rounded-panel border p-6", featured ? "border-ink bg-raised" : "border-line")}>
                  <h2>{p.name}</h2>
                  <p className="mt-4"><span className="font-display text-3xl font-semibold">{price(p)}</span>
                    {p.prices[currency] ? <span className="text-muted"> {t("price.month")}</span> : null}</p>
                  <ul className="mt-6 flex flex-col gap-2 text-[15px]">
                    {p.features.map((f) => <li key={f} className="flex gap-2"><Check size={18} className="mt-0.5 shrink-0" aria-hidden />{tx(`price.feat.${f}`, f)}</li>)}
                  </ul>
                  <dl className="mt-6 flex flex-col gap-1 border-t border-line pt-4 text-sm">
                    {Object.entries(p.limits).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-3"><dt className="text-muted">{tx(`price.limits.${k}`, k)}</dt><dd>{v === -1 ? t("price.unlimited") : v}</dd></div>
                    ))}
                  </dl>
                  <div className="mt-auto pt-6">
                    {current ? <p className="text-sm font-medium">{t("price.current")}</p> : p.code === "free" ? null : (
                      <Button className="w-full" variant={featured ? "primary" : "outline"} onClick={() => choose(p.code)}>{t("price.choose")}</Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
